# MISSION 03 KALAM — File 3: Mistake Analysis & Edge Cases
**Team:** antigravity | **Classification:** Adversarial Testing & Production Readiness v2.0 (Updated with Full Implementation)

---

## Table of Contents
1. [Adversarial Edge-Case Testing (10 Cases)](#1-adversarial-edge-case-testing)
2. [Production-Readiness Gaps](#2-production-readiness-gaps)
3. [Prompt Log Template](#3-prompt-log-template)
4. [**[NEW] Edge Case → Code Mapping**](#4-edge-case--code-mapping)
5. [**[NEW] Frontend Testing Checklist**](#5-frontend-testing-checklist)
6. [**[NEW] Implementation Lessons & Hardening Notes**](#6-implementation-lessons--hardening-notes)

---

## Testing Philosophy

> The system's adversarial behavior target is NOT "always find an answer."
> It is **"always fail clearly, explain the failure, and suggest a human escalation path."**
> A hallucinated eligibility determination is catastrophically worse than an honest "cannot determine."

**Scoring Key:**
- `0.9–1.0` = All hard conditions confirmed, no missing data, no ambiguities
- `0.7–0.89` = All hard conditions likely met; minor soft condition uncertainty
- `0.5–0.69` = Hard conditions partially confirmed; significant missing data
- `0.3–0.49` = Core eligibility unclear; ambiguity or contradiction present
- `0.0–0.29` = Disqualified or fundamentally unable to determine
- `BLOCKED`  = Eligible in principle but prerequisite missing (e.g., no bank account)

---

## 1. Adversarial Edge-Case Testing

### EC-01: Widow Who Recently Remarried

**User Profile:**
```
Age: 52 | Female | State: Rajasthan | Widow (govt records) | Remarried 1 year ago
BPL: Yes | Bank: Yes | Aadhaar: Yes | Currently receiving IGNWPS: Yes
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| IGNWPS (Widow Pension) | ❌ INELIGIBLE | 0.0 | Remarriage triggers hard exclusion |
| IGNOAPS | ❌ INELIGIBLE | 0.0 | Age 52 < 60 |
| PMSBY | ✅ QUALIFIED | 0.92 | Age 18–70, bank confirmed |
| PDS/NFSA | ✅ LIKELY QUALIFIED | 0.85 | BPL card present |
| PMJAY | 🟡 CHECK | 0.35 | SECC status unknown |

**System Behavior Contract:**
```
✓ Detects contradiction: "widow" → "naya pati" → sets remarried=True
✓ IGNWPS exclusion: remarried==True → confidence=0.0, status=INELIGIBLE
✓ NEVER says: "Since records still show widow, you can continue receiving"
✓ NEVER silently ignores the remarriage disclosure
✓ Flags ongoing pension as potentially irregular
✓ Escalation path: "BDO office ya District Social Welfare Officer se milein"
✓ Does NOT speculate on pension recovery (legal matter — human officer)
```

**Code Implementation:**
```python
# In app.py — IGNWPS exclusion check
{"field": "remarried", "op": "eq", "value": True,
 "source_clause": "NSAP 2016, Para 4.3 — widow status terminates on remarriage"},

# In _rule_based_extract — contradiction trigger
if any(w in t for w in ["dobaara","remarried","dusri shadi","naya pati"]):
    fields["remarried"] = True  # This triggers IGNWPS exclusion automatically

# In handle_contradiction — widow → remarried escalation
if field == "marital_status" and old_val == "widow" and new_value in ("married","remarried"):
    profile.remarried.value = True
    return "⚠️  RUKO — Aapne pehle kaha aap VIDHWA hain. Abhi aapne 'naya pati' mention kiya..."
```

---

### EC-02: Farmer Who Leases Land (Not Owner)

**User Profile:**
```
Age: 45 | Bihar | Occupation: Farmer | Cultivates 3 acres (LEASED)
Income: ₹60,000 | Bank: Yes | Aadhaar: Yes | Non-taxpayer
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| PM-KISAN | 🟡 AMBIGUOUS | 0.40 | Central rules require ownership; Bihar has not extended to lessees |
| MGNREGA | ✅ QUALIFIED | 0.91 | Rural, 18+, regardless of land |
| PMSBY | ✅ QUALIFIED | 0.93 | Age/bank confirmed |
| PMJJBY | ✅ QUALIFIED | 0.91 | Age < 50, bank confirmed |
| APY | ❌ INELIGIBLE | 0.0 | Age 45 > 40 upper limit |

**System Behavior:**
```
✓ Does NOT confidently say "qualify" or "disqualify" for PM-KISAN
✓ Ambiguity flag A01_LESSEE_FARMER caps confidence at 0.75 → raw 0.40 → AMBIGUOUS
✓ "Bihar has NOT formally extended PM-KISAN to lessees in gazette"
✓ Escalation: "Block Agriculture Officer se confirm karein"
✓ APY: correctly ineligible (age 45 > 40) — NOT ambiguous, hard fail
```

**Code Implementation:**
```python
# PM-KISAN hard condition
{"field": "land_ownership_status", "op": "in", "value": ["owner","joint_owner"]},
# "lessee" is NOT in this list → result = False → hard_scores.append(0.0)
# But ambiguity_flags=["A01_LESSEE_FARMER"] → could be state extension
# Resolution: output AMBIGUOUS, not INELIGIBLE

# APY hard condition
{"field": "age", "op": "lte", "value": 40},
# age=45 → result = False → hard fail → status=INELIGIBLE, confidence=0.0
```

---

### EC-03: Person with Aadhaar but No Bank Account

**User Profile:**
```
Age: 34 | Jharkhand | Agricultural laborer | Income: ₹45,000
BPL: Yes | Aadhaar: Yes | Bank Account: NO | Rural | SECC Listed: Yes
Housing: Kaccha house
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| PMJAY | ✅ QUALIFIED | 0.88 | SECC listed — no bank required for health card |
| MGNREGA | 🟡 BLOCKED | 0.55 | Eligible but wages need bank — PMJDY first |
| PMAY-G | 🟡 BLOCKED | 0.60 | Eligible but DBT subsidy needs bank |
| PMJDY | ✅ ACTION REQUIRED | 1.0 | This IS the prerequisite — open today |
| PM-KISAN | 🟡 BLOCKED | 0.40 | No bank = no DBT = blocked |

**Critical Distinction:**
```
INELIGIBLE ≠ BLOCKED

INELIGIBLE: User fails a hard eligibility condition (age, occupation, etc.)
BLOCKED:    User meets eligibility conditions but is missing a prerequisite to RECEIVE benefits

PMJAY is NOT blocked because health insurance card issuance ≠ DBT transfer.
MGNREGA/PMAY-G are BLOCKED (not ineligible) because wages/subsidies come via DBT.

System NEVER says "you are ineligible" for blocked schemes.
```

**Code Implementation:**
```python
# In match_scheme — BLOCKED status determination
if missing_fields and not failed_hard:
    # bank_account missing but all other conditions met → BLOCKED (not INELIGIBLE)
    status = MatchStatus.BLOCKED if "bank_account" in missing_fields \
             else MatchStatus.REQUIRES_VERIFICATION

# PMJDY is a prerequisite for DBT schemes
# prerequisites: ["S13"] in S01, S10, S11 → DAG resolution shows PMJDY first
```

---

### EC-04: Census Town Resident (Urban-Rural Boundary)

**User Profile:**
```
Age: 29 | Deoghar Ward 15, Jharkhand (Census Town — administrative urban, physically rural)
Occupation: Daily wage laborer | Income: ₹36,000/year
Bank: Yes | Aadhaar: Yes | BPL: Yes
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| MGNREGA | 🟡 AMBIGUOUS | 0.35 | Census Towns = urban. MGNREGA = rural ONLY |
| PMAY-G | ❌ INELIGIBLE | 0.0 | Gramin scheme — Census Town is urban |
| PMAY-U | 🟡 REQUIRES VERIFICATION | 0.55 | Urban scheme applies but state list may not include Census Town |
| PMSBY | ✅ QUALIFIED | 0.93 | No urban/rural restriction |
| PMJJBY | ✅ QUALIFIED | 0.91 | No urban/rural restriction |

**System Behavior:**
```
✓ Detects Census Town from district + ward data cross-reference
✓ Does NOT assume rural just because user says "gaon jaisa hai yahan"
✓ Outputs boundary ambiguity for affected schemes
✓ Outputs dual analysis (rural + urban) with disclaimer
✓ Escalation: "Apne BDO se confirm karein ki aapka ward rural ya urban mein aata hai"
```

**Ambiguity Flag:** `A06_URBAN_RURAL_BOUNDARY`

---

### EC-05: Person with Contradictory Income Evidence

**User Profile:**
```
Age: 42 | UP | Self-employed (mobile repair shop)
Stated Income: ~₹1,00,000/year
CONTRADICTIONS: Has GST (could be voluntary); has car; pucca house owned
Income Tax: "Nahi bharta"
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| PM-KISAN | ❌ INELIGIBLE | 0.0 | Not a farmer — occupation disqualifies |
| APY | ❌ INELIGIBLE | 0.0 | Age 42 > 40 |
| PMSBY | ✅ QUALIFIED | 0.90 | No income ceiling |
| PMAY-U | ❌ INELIGIBLE | 0.0 | Pucca house hard exclusion |

**System Behavior:**
```
✓ Does NOT auto-correct stated income based on GST/car
✓ Applies stated income with reduced confidence (0.6 from 1.0)
✓ Logs contradiction in audit trail
✓ Does NOT accuse user of fraud
✓ "Income certificate from tehsil would clarify"
✓ GST registration ≠ income_tax_payer (important distinction — see PL-250615-007)
```

---

### EC-06: Minor Applying on Behalf of Elder (Proxy Scenario)

**Profile Mismatch:**
```
Actual user: Anjali, age 17 (minor)
Beneficiary: Grandmother Kamla Devi, age 68 (BPL, widow, bank+Aadhaar)
Problem: Anjali answers questions about herself, not grandmother
```

**System Behavior:**
```
DETECTION: age=17 + "student" + questions about "nani ki pension"
→ Proxy scenario detected

✓ System asks: "Kya aap apne liye puch rahe hain, ya kisi aur ke liye?"
✓ If proxy: session data cleared, re-collected for BENEFICIARY
✓ Audit flag: "Data collected via proxy — identity verification at CSC required"
✓ Kamla Devi's actual profile → IGNOAPS qualified (age 68, BPL)
✓ IGNWPS also matches but overlaps IGNOAPS → "cannot get both" note added
```

---

### EC-07: Disability with Expired/Outdated Certificate

**User Profile:**
```
Age: 35 | MP | Disability: polio-affected leg
Disability %: "Doctor ne 60% bola tha 10 saal pehle"
Certificate: Old pre-SADM format | UDID: No | BPL: Yes | Bank+Aadhaar: Yes
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| IGNDPS | 🟡 BLOCKED | 0.30 | 60% < 80% required — but also old cert/no UDID |
| MGNREGA | ✅ QUALIFIED | 0.90 | No disability restrictions |
| PMSBY | ✅ QUALIFIED | 0.93 | No disability restrictions |

**System Behavior:**
```
✓ Does NOT accept self-reported % at face value for IGNDPS
✓ Notes UDID as required for modern enrollment
✓ Does NOT disqualify — flags for reassessment
✓ Output: "Naya SADM certificate banwana zaroori hoga. UDID: swavlambancard.gov.in"
✓ BLOCKED (not INELIGIBLE) because eligibility is plausible pending cert update
```

---

### EC-08: Urban Slum Dweller Without Proof of Residence

**User Profile:**
```
Age: 28 | Maharashtra | Mumbai slum/jhuggi settlement
Occupation: Domestic worker | Income: ₹72,000/year
Aadhaar: Yes (old UP village address) | Bank: Jan Dhan | BPL: Unknown
Residence Proof: NONE (Aadhaar shows UP address)
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| PMAY-U | 🟡 BLOCKED | 0.25 | Eligible on income but no local residence proof |
| PMJAY | 🟡 AMBIGUOUS | 0.30 | SECC 2011 likely covers UP village, not Mumbai |
| PDS/NFSA | 🟡 BLOCKED | 0.20 | UP ration card not portable to Maharashtra |
| PMSBY | ✅ QUALIFIED | 0.92 | No residence proof required |
| MGNREGA | ❌ INELIGIBLE | 0.0 | Urban — not covered |
| ONORC | ✅ ACTION | — | One Nation One Ration Card enables UP card in Maharashtra |

**System Behavior:**
```
✓ Does not fabricate path to PMAY-U without residence proof
✓ Explicitly states the cross-state documentation problem
✓ Provides choice: update Aadhaar address Mumbai OR use UP-based schemes
✓ NGO escalation: "YUVA / Apnalaya — Mumbai slum documentation help"
✓ Admits system limitation honestly: "Ye ek category hai jise hum poori tarah help nahi kar sakte"
```

---

### EC-09: Scheduled Tribe Member from Unsurveyed Forest Village

**User Profile:**
```
Age: 38 | Chhattisgarh | Gondi ST community | Forest village (not FRA surveyed)
Occupation: Subsistence farming | Income: ~₹30,000 (barter + minimal cash)
Land: Cultivates but NO formal patta | Aadhaar: Yes | Bank: Jan Dhan | BPL: Unknown
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| PM-KISAN | ❌ BLOCKED | 0.10 | No formal land record |
| PMAY-G | ❌ BLOCKED | 0.15 | SECC 2011 may not cover unsurveyed village |
| MGNREGA | 🟡 AMBIGUOUS | 0.50 | Technically rural adult — but Van Gram Panchayat status creates Job Card friction |
| FRA Patta | 📌 PREREQUISITE | — | Forest Rights Act claim must be filed FIRST |

**System Behavior:**
```
✓ Identifies documentation blackhole for unsurveyed forest villages
✓ Does NOT proceed with high-confidence eligibility
✓ Identifies FRA patta as foundational prerequisite
✓ Escalation: "Van Adhikar Samiti / Ekta Parishad / CGNET Swara"
✓ Honest system limitation: standard eligibility framework has limited coverage here
```

---

### EC-10: Returnee Migrant Worker (Inter-State, Multiple Profiles)

**User Profile:**
```
Age: 31 | Native: Bihar (all schemes registered there) | Working: Gujarat (textile factory)
Occupation: Factory worker (BUT registered as kisan in Bihar for PM-KISAN)
Income: ₹1,80,000/year | Bank: Bihar Jan Dhan | Ration Card: Bihar PHH
```

**Expected System Output:**

| Scheme | Status | Confidence | Reason |
|---|---|---|---|
| PM-KISAN | ❌ DISQUALIFIED | 0.05 | Actual occupation = factory worker, not farmer |
| MGNREGA | ❌ INELIGIBLE | 0.0 | Urban Gujarat factory |
| ONORC | ✅ QUALIFIED | 0.88 | Bihar ration card usable in Gujarat |
| PMSBY | ✅ QUALIFIED | 0.92 | No state restriction |
| e-Shram Card | ✅ QUALIFIED | 0.90 | Unorganised migrant worker — eshram.gov.in |

**System Behavior:**
```
✓ Detects conflict: Bihar "farmer" record vs Gujarat factory occupation
✓ Flags PM-KISAN as potentially irregular — does NOT advise continuing
✓ Key outputs: e-Shram card + ONORC as migrant-specific entitlements
✓ Escalation for PM-KISAN: "Apne tehsil / agriculture officer ko sthiti batayein"
```

---

## 2. Production-Readiness Gaps

### Gap 1: SECC 2011 Data is 13 Years Old

**Problem:** SECC 2011 determines eligibility for PMJAY, PMAY-G, and several NSAP schemes. The data is from 2011 — 13+ years ago. Families who became poorer post-2011 are excluded; families who improved may still be listed.

**Current System Response:**
```
Ambiguity flag: A04_SECC_DATA_STALENESS
Output: "Hum SECC data override nahi kar sakte. 14555 ya pmjay.gov.in par check karein."
```

**Production Hardening Required:**
```
v1: Detect high-probability SECC eligibility from proxy indicators (BPL card, kaccha house, ST category)
    → output "LIKELY listed — verify at portal"
v2: API integration with pmjay.gov.in eligibility check (if/when API made available)
v3: State-level SECC expansion tracking (some states added non-SECC families)
```

**Estimated Impact:** Affects 3 of 15 schemes. ~40% of rural users hit this gap.

---

### Gap 2: State-Level Scheme Rules Not Implemented

**Problem:** Every central scheme has state-level overrides (different income ceilings, different document requirements, additional state top-ups). Currently only PM-KISAN West Bengal override is implemented as example.

**States requiring priority implementation:**

| State | Key Override |
|---|---|
| West Bengal | PM-KISAN blocked for Krishak Bandhu enrollees |
| Telangana | Rythu Bandhu replaces PM-KISAN |
| Odisha | KALIA scheme → different farmer eligibility |
| Tamil Nadu | Chief Minister schemes expand PMAY eligibility |
| Rajasthan | Chiranjeevi Yojana expands PMJAY to all residents |

**Resolution:** State-variant JSONB columns + runtime merger:
```python
def apply_state_overrides(scheme: dict, state: str) -> dict:
    """Merge state-level overrides into central scheme rules."""
    variants = scheme.get("state_variants", {})
    state_code = STATE_CODES.get(state)
    if state_code and state_code in variants:
        override = variants[state_code]
        if "additional_conditions" in override:
            scheme["hard_conditions"].extend(override["additional_conditions"])
        if "income_ceiling_override" in override:
            # Replace income condition value
            for cond in scheme["hard_conditions"]:
                if cond["field"] == "annual_income":
                    cond["value"] = override["income_ceiling_override"]
    return scheme
```

---

### Gap 3: No Persistent Database (Dev vs Production)

**Current State:** Session data stored in Python dict (`_SESSIONS = {}`) — lost on server restart.

**Production Path:**
```bash
# Step 1: Add Redis dependency
pip install redis

# Step 2: Replace in app.py
import redis
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

def save_session(profile: UserProfile):
    r.setex(f"session:{profile.session_id}", 1800, profile.json())

def load_session(session_id: str) -> Optional[UserProfile]:
    data = r.get(f"session:{session_id}")
    return UserProfile.parse_raw(data) if data else None
```

---

### Gap 4 [NEW]: Frontend Has No Backend Connection (Demo Mode)

**Current State:** `index.html` uses client-side JavaScript for all responses (no API call).

**Production Connection:**
```javascript
// Add to index.html sendMessage() function:
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg   = input.value.trim();
    if (!msg) return;
    addMsg(msg, 'user');
    input.value = '';
    showTyping();

    try {
        const resp = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: SESSION_ID, message: msg, channel: 'web' })
        });
        const data = await resp.json();
        SESSION_ID = data.session_id;
        removeTyping();
        addMsg(data.reply, 'bot');
        updateStatCards(data);
        // Re-render schemes with real confidence scores
        renderSchemeResults(data.scheme_matches);
    } catch(e) {
        removeTyping();
        addMsg(getBotResponse(msg), 'bot');  // Fallback to offline mode
    }
}
```

---

## 3. Prompt Log Template

### 3.1 Template Structure

```yaml
entry_id: "PL-YYMMDD-NNN"
timestamp: "YYYY-MM-DD HH:MM:SS UTC"

session_context:
  task_phase: "Rule Engine | NLU | Frontend | Gap Analysis | Testing"
  component_being_built: "<specific component>"
  human_intent: "<what you were trying to accomplish>"

prompt:
  model_used: "claude-sonnet-4-20250514 | gpt-4o"
  temperature: 0.0
  system_prompt_used: "<None | NLU_SYSTEM_PROMPT | custom>"
  full_prompt: |
    <exact prompt text>

output:
  full_raw_output: |
    <exact model output — do not summarize>

evaluation:
  verdict: "ACCEPTED | PARTIALLY_ACCEPTED | REJECTED"

  modifications_made:        # If PARTIALLY_ACCEPTED
    - "<specific change 1>"
    - "<specific change 2>"

  rejection_reason: |        # If REJECTED
    <WHY was it rejected — specific, evidenced>

  specific_errors_found:
    - error_id: "E01"
      description: "<exact error>"
      severity: "CRITICAL | HIGH | MEDIUM | LOW"
      evidence: "<gazette clause, URL, or test case reference>"

  hallucination_flag: true/false
  hallucination_detail: |
    <What was fabricated and WHY it's wrong>

follow_up:
  human_work_required: |
    <What you had to do manually to correct or verify>
  final_code_committed: true/false
  commit_ref: "<git commit hash if applicable>"

metadata:
  logged_by: "<team member name>"
  time_spent_on_prompt_design: <minutes>
  time_spent_on_evaluation: <minutes>
  total_tokens_used: <integer>
  tags: ["<tag1>", "<tag2>"]
```

---

### 3.2 Sample Entries

#### Entry PL-250615-003 (PARTIALLY_ACCEPTED — Critical Omission Fixed)

```yaml
entry_id: "PL-250615-003"
timestamp: "2025-06-15 14:30:00 UTC"

session_context:
  task_phase: "Rule Engine"
  component_being_built: "IGNWPS (Widow Pension) scheme rule"
  human_intent: "Generate complete JSON rule for IGNWPS eligibility"

prompt:
  model_used: "claude-sonnet-4-20250514"
  temperature: 0.0
  system_prompt_used: "None"
  full_prompt: |
    Generate a complete eligibility rule for IGNWPS (Indira Gandhi National Widow Pension Scheme)
    as a Python dict following the SchemeEligibilityRule schema.
    Include all hard conditions, soft conditions, exclusions, required documents.

output:
  full_raw_output: |
    {
      "scheme_id": "S08",
      "scheme_name": "IGNWPS (Widow Pension)",
      "hard_conditions": [
        {"field": "gender", "op": "eq", "value": "female"},
        {"field": "marital_status", "op": "eq", "value": "widow"},
        {"field": "age", "op": "gte", "value": 40},
        {"field": "age", "op": "lte", "value": 79},
        {"field": "bpl_category", "op": "eq", "value": True}
      ],
      "exclusions": [
        {"field": "existing_pension_any_source", "op": "eq", "value": True}
      ]
    }

evaluation:
  verdict: "PARTIALLY_ACCEPTED"

  modifications_made:
    - "Added remarried exclusion: {'field': 'remarried', 'op': 'eq', 'value': True}"
    - "Added ambiguity_flags: ['A10_WIDOW_REMARRIAGE_STATUS']"

  specific_errors_found:
    - error_id: "E01"
      description: "AI omitted remarriage exclusion. A remarried woman is NOT a widow
                    under NSAP rules — she loses eligibility. This omission would cause
                    false-positive eligibility for EC-01 case."
      severity: "CRITICAL"
      evidence: "NSAP Guidelines 2016, Para 4.3: 'widow' status terminates upon remarriage."

  hallucination_flag: false
  hallucination_detail: "N/A — omission, not fabrication"

follow_up:
  human_work_required: |
    Manually added remarriage exclusion after cross-checking NSAP 2016 guidelines PDF.
    Added EC-01 to adversarial test suite.
    Team discussion: AI models the 'simple' case and misses edge case exclusions.
    Rule: All exclusion lists MUST be manually verified against gazette text.
  final_code_committed: true
  commit_ref: "abc1234"

metadata:
  logged_by: "Arjun (team lead)"
  time_spent_on_prompt_design: 15
  time_spent_on_evaluation: 25
  total_tokens_used: 850
  tags: ["scheme-rules","ignwps","widow-pension","exclusion-logic","CRITICAL-FIXED"]
```

---

#### Entry PL-250615-007 (REJECTED — Hallucination)

```yaml
entry_id: "PL-250615-007"
timestamp: "2025-06-15 19:15:00 UTC"

session_context:
  task_phase: "Rule Engine"
  component_being_built: "PM-KISAN income threshold rule"
  human_intent: "Verify PM-KISAN income exclusion threshold"

prompt:
  model_used: "gpt-4o"
  temperature: 0.0
  full_prompt: |
    What is the income ceiling for PM-KISAN eligibility?
    Is there an annual household income threshold that disqualifies a farmer?
    Cite the official source.

output:
  full_raw_output: |
    PM-KISAN has an income ceiling of Rs. 6 lakh per annum for household eligibility.
    Farmers with annual household income above Rs. 6 lakh are disqualified.
    Source: PM-KISAN operational guidelines, 2020 revision.

evaluation:
  verdict: "REJECTED"

  rejection_reason: |
    HALLUCINATION: PM-KISAN does NOT have an income ceiling in rupee terms.
    The exclusions are CATEGORICAL (income taxpayer, professional, govt employee).
    NOT a specific rupee threshold. The AI invented "Rs. 6 lakh" —
    this number does not appear in any PM-KISAN gazette notification.

  specific_errors_found:
    - error_id: "E07"
      description: "AI fabricated an income ceiling of Rs. 6 lakh for PM-KISAN.
                    No such threshold exists. If deployed, this would incorrectly
                    disqualify thousands of eligible farmers."
      severity: "CRITICAL"
      evidence: "PM-KISAN Operational Guidelines 2019, Para 6 — lists exclusions.
                 No income ceiling in rupees exists.
                 Verified: https://pmkisan.gov.in/Documents/Operational_Guidelines.pdf"

  hallucination_flag: true
  hallucination_detail: |
    AI confused income thresholds from OTHER schemes (APY, some state schemes)
    and applied them to PM-KISAN.
    LESSON: For ALL numeric thresholds — DO NOT trust AI output.
    Always verify against primary gazette. AI training data may contain
    incorrect secondary sources.

follow_up:
  human_work_required: |
    1. Verified against PM-KISAN gazette — confirmed NO income ceiling in rupees
    2. Team rule added: "All numeric thresholds require primary source citation.
       AI-generated thresholds without URL citation are auto-flagged."
    3. Added to validation checklist: "Does this scheme have an income ceiling?
       If yes — cite exact gazette clause."
  final_code_committed: false

metadata:
  logged_by: "Priya"
  time_spent_on_evaluation: 40
  tags: ["scheme-rules","pm-kisan","hallucination","income-threshold","CRITICAL-REJECTED"]
```

---

### 3.3 Aggregate Metrics Template

```markdown
## Prompt Log Summary — Week [N]
**Date Range:** [YYYY-MM-DD] to [YYYY-MM-DD]
**Total Entries:** ___

### Verdict Distribution
| Verdict | Count | % |
|---|---|---|
| ACCEPTED (verbatim) | ___ | ___% |
| PARTIALLY_ACCEPTED  | ___ | ___% |
| REJECTED            | ___ | ___% |

### Rejection Reasons
| Reason | Count |
|---|---|
| HALLUCINATION | ___ |
| WRONG_LOGIC | ___ |
| WRONG_THRESHOLD | ___ |
| AMBIGUITY_IGNORED | ___ |
| SAFETY_CONCERN | ___ |

### Hallucination Rate
- hallucination_flag: true count: ___
- Rate: ___%
- Most common: ___

### Net Productivity
- Time evaluating + correcting: ___ hours
- Time saved vs. writing from scratch: ___ hours
- Net gain: ___ hours
```

### 3.4 Anti-Patterns (What NOT to Log)

```
❌ BAD: "Prompt: 'Write eligibility rules'. Output: [accepted]. No errors."
   WHY: No evaluation. This is logging AI use without critical thinking.

❌ BAD: "Output was good. Used it."
   WHY: "Good" by what standard? No evidence of verification.

❌ BAD: Logging only ACCEPTED entries.
   WHY: Rejections are where learning happens. Zero rejections = not evaluating.

❌ BAD: Modifying AI output without noting what changed.
   WHY: "Cleaned up" is not traceable.

✅ GOOD: "AI said Rs. 6L threshold — gazette says no income ceiling. Rejected.
   See PM-KISAN Guidelines Para 6."

✅ GOOD: "Third time AI missed a remarriage edge case. Adding explicit instruction
   to all rule-generation prompts: 'List ALL exclusions including remarriage,
   death, fraudulent enrollment scenarios.'"

✅ GOOD: "Tried Chain-of-Thought — worse than direct format constraint. Reverted."
```

---

## 4. Edge Case → Code Mapping

| Edge Case | Ambiguity Flag | Code Location | Handler |
|---|---|---|---|
| EC-01: Widow remarried | A10 | IGNWPS exclusions | `{"field":"remarried","op":"eq","value":True}` |
| EC-02: Lessee farmer | A01 | PM-KISAN hard conditions | `"land_ownership_status" in ["owner","joint_owner"]` — lessee not included |
| EC-03: No bank account | A12 | `match_scheme()` | `status = BLOCKED if "bank_account" in missing_fields` |
| EC-04: Census Town | A06 | `residence_type` detection | Dual rural/urban analysis with disclaimer |
| EC-05: GST ≠ income tax | — | NLU system prompt rule 8 | "GST filing does NOT imply income_tax_payer: true" |
| EC-06: Proxy session | — | FSM / handle_proxy() | Age + context → re-collect for beneficiary |
| EC-07: Old disability cert | A11 | IGNDPS gap_analysis | Flag UDID registration as prerequisite |
| EC-08: Cross-state migrant | — | `residence_type` + `state` | Dual-state documentation check |
| EC-09: Forest village ST | — | `land_ownership_status` | FRA patta as prerequisite in DAG |
| EC-10: Migrant factory worker | — | Occupation conflict detection | "farmer" in Bihar records vs factory occupation |

---

## 5. Frontend Testing Checklist

### 5.1 Chat Behavior Tests

```
[ ] Hinglish input correctly triggers rule-based fallback when LLM unavailable
[ ] "Dobaara shaadi" / "naya pati" triggers remarried=True and IGNWPS exclusion
[ ] "Aadhaar nahi" sets aadhaar=False and triggers PMJDY prerequisite response
[ ] "Bank nahi" sets bank_account=False and shows BLOCKED status for DBT schemes
[ ] Widow contradiction detected: first "vidhwa" then "naya pati"
[ ] Contradiction handler shows ⚠️ and asks clarifying question
[ ] Profile completion % updates after each field extraction
[ ] "Shukriya" / "thanks" triggers farewell response
```

### 5.2 Scheme Display Tests

```
[ ] All 15 schemes appear in Schemes panel
[ ] Confidence bars animate from 0% to final value
[ ] QUALIFIED shown in green (≥80%)
[ ] REQUIRES_VERIFICATION shown in orange (50-79%)
[ ] INELIGIBLE shown in red/pink (<50% or hard exclusion)
[ ] BLOCKED shown differently from INELIGIBLE
[ ] Scheme cards in mini grid show correct status badges
```

### 5.3 Gap Analysis Tests

```
[ ] HIGH priority gaps shown first
[ ] Fields affecting 3+ schemes marked HIGH
[ ] Each gap has actionable "how_to_obtain" text in Hinglish
[ ] PMJDY shown as ACTION REQUIRED when bank_account=False
[ ] Missing aadhaar shows SADM/Aadhaar centre guidance
```

### 5.4 Cross-Device Tests

```
[ ] Sidebar collapses on mobile viewport
[ ] Chat input keyboard doesn't push layout on iOS
[ ] WhatsApp-style message bubbles render correctly
[ ] Offline mode (no API) falls back to rule-based JS responses
[ ] index.html opens correctly when opened as local file (file:// protocol)
```

---

## 6. Implementation Lessons & Hardening Notes

### L-01: AI Always Models the Simple Case

**Observation:** In 3 of 5 scheme rule generation prompts, the AI generated the standard eligibility case correctly but missed edge case exclusions (remarriage, proxy enrollment, state overrides).

**Hardening Rule:** Add to all rule-generation prompts:
```
"List ALL exclusions including:
- Remarriage, death, or change in beneficiary status
- Geographic boundary cases (Census Town, forest village)
- Prior scheme enrollment (no double-dipping clauses)
- Fraudulent or informal enrollment in old records
- Cross-state migration scenarios"
```

---

### L-02: Never Trust AI for Numeric Thresholds Without Primary Source

**Evidence:** PL-250615-007 — AI fabricated ₹6L income ceiling for PM-KISAN.

**Team Rule:** Every numeric threshold in a scheme rule requires:
1. Gazette URL or document reference
2. Human verification against primary document
3. Committed to scheme validation checklist

---

### L-03: INELIGIBLE vs BLOCKED is a Critical UX Distinction

**Observation:** Early prototype showed "INELIGIBLE" for schemes where the user was actually eligible but missing a prerequisite (bank account). This caused user distress and incorrect escalation.

**Fix:** Added `MatchStatus.BLOCKED` distinct from `INELIGIBLE`. Updated all UI labels and colors.

```python
# WRONG (v1):
if missing_fields: status = MatchStatus.INELIGIBLE  # ❌ Wrong — user is eligible!

# CORRECT (v2):
if missing_fields and not failed_hard:
    status = MatchStatus.BLOCKED  # ✅ Eligible, but prerequisite missing
```

---

### L-04: Frontend Offline Mode is a Feature, Not a Bug

**Context:** Many CSC field operators have intermittent internet. The rule-based JavaScript fallback in `index.html` allows the UI to function without API connectivity.

**Guideline:** Every feature added to the backend `/chat` API must have a corresponding client-side fallback in `index.html`.

---

### L-05: The Explainability Contract Must Be Tested Automatically

**Rule:** Before any `SchemeMatchResult` is shown to a user, `validate_explainability_contract()` must pass. Add this as a unit test assertion in CI:

```python
def test_explainability_all_schemes():
    test_profile = UserProfile(session_id="test", channel="test")
    for scheme in SCHEMES.values():
        result = match_scheme(scheme, test_profile)
        assert validate_explainability_contract(result), \
            f"Explainability violation for {scheme['scheme_name']}"
```

---

## Appendix: File Index

| File | Contents | Status |
|---|---|---|
| `1_backend_and_architecture.md` | Architecture, technical decisions, 15 scheme rules, ambiguity map, matching engine, **FastAPI backend spec, frontend architecture, API reference** | ✅ v2.0 |
| `2_frontend_and_conversational_ui.md` | State management, Hinglish NLP, FSM flows, contradiction handler, 2 transcripts, **NanoAI dashboard design spec, component breakdown, API integration** | ✅ v2.0 |
| `3_mistake_analysis_and_edge_cases.md` | 10 adversarial edge cases, 4 production gaps, prompt log template, **edge case → code mapping, frontend test checklist, implementation lessons** | ✅ v2.0 |
| `kalam_frontend/index.html` | Complete NanoAI-style HTML/CSS/JS dashboard (offline-capable) | ✅ New |
| `kalam_backend/app.py` | Complete FastAPI backend — NLU, rule engine, gap analysis, session management | ✅ New |

**Team Antigravity — Mission 03 Kalam** ✅
*"Always fail clearly, explain the failure, and suggest a human escalation path."*