from typing import Optional, List
from models import UserProfile, SchemeMatchResult, GapItem, DataSource
from schemes_db import FIELD_GUIDANCE

def eval_condition(cond: dict, flat: dict) -> Optional[bool]:
    field = cond["field"]
    op = cond["op"]
    val = cond.get("value")
    user_val = flat.get(field)

    if user_val is None:
        return None  

    try:
        if op == "eq":     return user_val == val
        if op == "neq":    return user_val != val
        if op == "lt":     return float(user_val) < float(val)
        if op == "lte":    return float(user_val) <= float(val)
        if op == "gt":     return float(user_val) > float(val)
        if op == "gte":    return float(user_val) >= float(val)
        if op == "in":     return user_val in val
        if op == "not_in": return user_val not in val
    except (TypeError, ValueError):
        return None
    return None

def match_scheme(scheme: dict, profile: UserProfile) -> SchemeMatchResult:
    flat = profile.to_flat_dict()
    missing_fields = []
    failed_hard = []
    triggered_excl = []

    # PHASE 1: Exclusions — ANY True = INELIGIBLE
    for cond in scheme.get("exclusions", []):
        result = eval_condition(cond, flat)
        if result is True:
            triggered_excl.append(cond["field"])
            return SchemeMatchResult(
                scheme_id=scheme["scheme_id"],
                scheme_name=scheme["scheme_name"],
                status="INELIGIBLE",
                confidence_score=0.0,
                confidence_breakdown={"exclusion_triggered": cond["field"]},
                missing_fields=[],
                failed_hard_conditions=[],
                triggered_exclusions=triggered_excl,
                ambiguity_flags=scheme.get("ambiguity_flags", []),
                application_sequence=[],
                explanation=f"❌ Ineligible: {cond['field']} exclusion triggered.",
                benefit_summary=scheme.get("benefit_summary", ""),
                required_docs=scheme.get("required_docs", []),
                next_action="Aap is scheme ke liye eligible nahi hain."
            )

    # PHASE 2: Hard Conditions — ALL must be True
    hard_scores = []
    for cond in scheme.get("hard_conditions", []):
        result = eval_condition(cond, flat)
        if result is None:
            missing_fields.append(cond["field"])
            hard_scores.append(0.5)      
        elif result is True:
            hard_scores.append(1.0)
        else:
            failed_hard.append(cond["field"])
            hard_scores.append(0.0)

    hard_avg = sum(hard_scores) / max(len(hard_scores), 1)

    # PHASE 3: Soft Conditions
    soft_scores = []
    SOFT_WEIGHT = 0.15
    for cond in scheme.get("soft_conditions", []):
        result = eval_condition(cond, flat)
        soft_scores.append(1.0 if result is True else 0.0)

    soft_bonus = (sum(soft_scores)/max(len(soft_scores),1)) * SOFT_WEIGHT if soft_scores else 0
    missing_penalty = len(missing_fields) * 0.10
    ambiguity_flags = scheme.get("ambiguity_flags", [])
    
    # Active ambiguities verification
    active_ambigs = []
    for am in ambiguity_flags:
        if am == "A01_LESSEE_FARMER" and flat.get("land_ownership_status") == "lessee":
            active_ambigs.append(am)
        if am == "A10_WIDOW_REMARRIAGE_STATUS" and flat.get("marital_status") == "widow" and flat.get("remarried") is None:
            active_ambigs.append(am)
        if am == "A04_SECC_STALENESS" and flat.get("secc_2011_listed") is None:
            active_ambigs.append(am)

    ambiguity_cap = 0.75 if active_ambigs else 1.0

    # Composite Score
    raw_score = min(1.0, hard_avg + soft_bonus - missing_penalty)
    final_score = round(min(raw_score, ambiguity_cap), 2)

    # Determine Status
    if final_score >= 0.85 and not missing_fields:
        status = "QUALIFIED"
    elif final_score >= 0.60:
        status = "LIKELY_QUALIFIED"
    elif missing_fields and not failed_hard:
        status = "BLOCKED" if "bank_account_linked_aadhaar" in missing_fields else "REQUIRES_VERIFICATION"
    elif active_ambigs:
        status = "AMBIGUOUS"
    else:
        status = "REQUIRES_VERIFICATION" if not failed_hard else "INELIGIBLE"

    if failed_hard:
        final_score = 0.0

    return SchemeMatchResult(
        scheme_id=scheme["scheme_id"],
        scheme_name=scheme["scheme_name"],
        status=status,
        confidence_score=final_score,
        confidence_breakdown={
            "hard_avg": round(hard_avg, 2),
            "soft_bonus": round(soft_bonus, 2),
            "missing_penalty": round(missing_penalty, 2),
            "ambiguity_cap": ambiguity_cap,
        },
        missing_fields=missing_fields,
        failed_hard_conditions=failed_hard,
        triggered_exclusions=[],
        ambiguity_flags=active_ambigs,
        application_sequence=[],
        explanation=f"Confidence: {int(final_score*100)}% | {status} | Missing: {missing_fields or 'None'}",
        benefit_summary=scheme.get("benefit_summary", ""),
        required_docs=scheme.get("required_docs", []),
        next_action=scheme.get("next_action", "")
    )

def do_gap_analysis(matches: List[SchemeMatchResult]) -> List[dict]:
    gaps = {}
    for result in matches:
        if result.status in ["REQUIRES_VERIFICATION", "LIKELY_QUALIFIED", "BLOCKED"]:
            for field in result.missing_fields:
                if field not in gaps:
                    gaps[field] = {
                        "field": field,
                        "affects_schemes": [],
                        "priority": "low",
                        "how_to_obtain": FIELD_GUIDANCE.get(field, f"Provide information on {field}"),
                    }
                gaps[field]["affects_schemes"].append(result.scheme_id)
    
    for info in gaps.values():
        n = len(info["affects_schemes"])
        info["priority"] = "high" if n >= 3 else "medium" if n >= 2 else "low"
    
    return sorted(gaps.values(), key=lambda x: {"high":0,"medium":1,"low":2}[x["priority"]])
