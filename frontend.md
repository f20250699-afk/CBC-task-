# MISSION 03 KALAM — File 2: Frontend & Conversational UI
**Team:** antigravity | **Classification:** Conversational Interface Design v2.0 (Updated with Full Implementation)

---

## Table of Contents
1. [UI/CLI Architecture & State Management](#1-uicli-architecture--state-management)
2. [Hinglish NLP Strategy](#2-hinglish-nlp-strategy)
3. [Conversation Flows (State Machine)](#3-conversation-flows-state-machine)
4. [Example Transcripts](#4-example-transcripts)
5. [**[NEW] NanoAI-Style Dashboard — Design Spec**](#5-nanoai-style-dashboard--design-spec)
6. [**[NEW] Frontend Component Breakdown**](#6-frontend-component-breakdown)
7. [**[NEW] API Integration Layer**](#7-api-integration-layer)

---

## 1. UI/CLI Architecture & State Management

### 1.1 Deployment Targets

| Channel | Technology | Rationale |
|---|---|---|
| **Web Dashboard** (primary v2) | Pure HTML/CSS/JS — NanoAI style | Zero framework dependencies; deployable from USB or static host |
| **CLI** (demo) | Python `rich` library + `prompt_toolkit` | Zero dependency on internet; works on field laptops |
| **WhatsApp Bot** | Twilio API + FastAPI webhook | Highest penetration in rural India; no app install needed |
| **CSC-assisted Web** | Same HTML + backend API | For Common Service Centre operator-assisted sessions |
| **IVRS (future)** | Twilio Voice + TTS/STR | For non-literate users; out of scope for v1 |

### 1.2 State Management Model

The conversation maintains a persistent, evolving `UserProfile` object across turns. The system handles:
- Users who don't know their own data (e.g., "Mujhe nahi pata mera income")
- Users who give contradictory data across turns
- Session interruptions and resumptions (WhatsApp especially)
- Graceful degradation when answers are missing

```python
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
import json, time

class DataSource(Enum):
    USER_STATED       = "user_stated"       # User explicitly told us
    USER_ESTIMATED    = "user_estimated"    # User said "approx" / "lagbhag"
    SYSTEM_INFERRED   = "system_inferred"   # System derived from other answers
    DEFAULT_ASSUMED   = "default_assumed"   # System assumed (flagged)
    UNKNOWN           = "unknown"           # User could not answer

@dataclass
class ProfileField:
    value: Optional[Any] = None
    source: DataSource = DataSource.UNKNOWN
    confidence: float = 0.0          # 0.0 = unknown, 0.5 = inferred, 1.0 = stated
    raw_utterance: str = ""          # What the user actually said (for audit)
    turn_number: int = 0             # Which conversation turn this was set in
    contradictions: list = field(default_factory=list)  # Prior conflicting values

@dataclass
class UserProfile:
    session_id: str
    channel: str                     # "cli", "whatsapp", "web"
    language_preference: str = "hinglish"

    # Core eligibility fields — each is a ProfileField
    age:                    ProfileField = field(default_factory=ProfileField)
    gender:                 ProfileField = field(default_factory=ProfileField)
    state:                  ProfileField = field(default_factory=ProfileField)
    district:               ProfileField = field(default_factory=ProfileField)
    residence_type:         ProfileField = field(default_factory=ProfileField)
    caste_category:         ProfileField = field(default_factory=ProfileField)
    annual_income:          ProfileField = field(default_factory=ProfileField)
    occupation:             ProfileField = field(default_factory=ProfileField)
    land_ownership_status:  ProfileField = field(default_factory=ProfileField)
    land_size_acres:        ProfileField = field(default_factory=ProfileField)
    family_size:            ProfileField = field(default_factory=ProfileField)
    marital_status:         ProfileField = field(default_factory=ProfileField)
    bank_account:           ProfileField = field(default_factory=ProfileField)
    aadhaar:                ProfileField = field(default_factory=ProfileField)
    bpl_category:           ProfileField = field(default_factory=ProfileField)
    secc_2011_listed:       ProfileField = field(default_factory=ProfileField)
    disability:             ProfileField = field(default_factory=ProfileField)
    housing_status:         ProfileField = field(default_factory=ProfileField)
    income_tax_payer:       ProfileField = field(default_factory=ProfileField)
    remarried:              ProfileField = field(default_factory=ProfileField)

    # Derived flags
    is_farmer: Optional[bool] = None

    # Session metadata
    created_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)
    turn_count: int = 0
    contradiction_log: list = field(default_factory=list)

    def to_flat_dict(self) -> dict:
        """Flatten ProfileField objects to values + confidence for Rule Engine."""
        result = {}
        for fname, fval in self.__dict__.items():
            if isinstance(fval, ProfileField):
                result[fname] = fval.value
                result[f"{fname}_confidence"] = fval.confidence
        return result

    def completion_pct(self) -> int:
        PRIORITY = ["state","residence_type","age","occupation","annual_income","gender",
                    "bank_account","aadhaar","bpl_category"]
        filled = sum(1 for f in PRIORITY if getattr(self, f).value is not None)
        return round((filled / len(PRIORITY)) * 100)

    def set_field(self, field_name, value, source, confidence, raw_utterance, turn):
        """Thread-safe field update with contradiction detection."""
        pf: ProfileField = getattr(self, field_name)
        if pf.value is not None and pf.value != value:
            pf.contradictions.append({
                "field": field_name, "old_value": pf.value, "new_value": value,
                "old_turn": pf.turn_number, "new_turn": turn,
            })
            self.contradiction_log.append(pf.contradictions[-1])
            return False  # Signal contradiction to FSM
        pf.value = value; pf.source = source; pf.confidence = confidence
        pf.raw_utterance = raw_utterance; pf.turn_number = turn
        self.last_updated_at = time.time()
        return True
```

### 1.3 Field Completion Tracker

```python
# Priority order: fields that unlock the most scheme-filtering come first
FIELD_PRIORITY_ORDER = [
    "state",              # Required for state variants
    "residence_type",     # Rural/urban splits ~half the schemes immediately
    "age",                # Eliminates pension and youth schemes
    "occupation",         # Farmer → PM-KISAN path
    "annual_income",      # BPL/income ceiling gates
    "gender",             # Widow pension, SSY
    "marital_status",     # Widow pension specifically
    "land_ownership_status",   # PM-KISAN, PMAY-G
    "bank_account",       # DBT requirement (BLOCKS multiple schemes)
    "aadhaar",            # Identity foundation
    "bpl_category",       # NSAP schemes
    "secc_2011_listed",   # PMJAY, PMAY-G
    "housing_status",     # PMAY
    "family_size",        # MGNREGA household unit
    "disability",         # IGNDPS
    "caste_category",     # Priority queuing (SC/ST)
    "income_tax_payer",   # Exclusion for PM-KISAN, APY
]

FIELD_QUESTIONS = {
    "state":                  "Aap kis state se hain? (e.g., Rajasthan, Bihar, MP)",
    "residence_type":         "Gaon mein rehte hain ya shahar mein? (Rural / Urban)",
    "age":                    "Aapki umar kitni hai?",
    "occupation":             "Aap kya kaam karte hain? (Kisan / Mazdoor / Naukri / Kuch nahi)",
    "annual_income":          "Saal ki family income kitni hai approximately?",
    "gender":                 "Aap purush hain ya mahila?",
    "marital_status":         "Aapki marital status? (Married / Widow / Single)",
    "land_ownership_status":  "Khet ya zameen hai aapke naam par?",
    "bank_account":           "Koi bank account hai? (Jan Dhan, SBI, Post Office — kuch bhi)",
    "aadhaar":                "Aadhaar card hai aapke paas?",
    "bpl_category":           "BPL card hai ya BPL list mein naam hai?",
    "secc_2011_listed":       "Ayushman Bharat ke baare mein — kya aapka naam SECC list mein hai?",
    "housing_status":         "Ghar ki sthiti? (Pakka / Kaccha / Koi ghar nahi)",
    "disability":             "Koi disability hai? (Haan / Nahi)",
}

def get_next_question(profile: UserProfile) -> Optional[str]:
    for field_name in FIELD_PRIORITY_ORDER:
        pf: ProfileField = getattr(profile, field_name, None)
        if pf and (pf.value is None or pf.source == DataSource.UNKNOWN):
            return FIELD_QUESTIONS.get(field_name)
    return None  # All priority fields collected
```

---

## 2. Hinglish NLP Strategy

### 2.1 The Core Problem

Pure rule-based NLP cannot handle:
- Code-switching: "Mera income around 80 hazaar hai per year"
- Vagueness: "Hum log gaon mein rehte hain" (implies rural but doesn't say it)
- Contradiction: "Main kisan hoon" then later "Main ek private company mein kaam karta hoon"
- Uncertainty: "Shayad BPL list mein naam hai, pakka nahi"
- Refusal: "Ye sab batana zaroori hai kya?"

### 2.2 NLU Pipeline Architecture

```
User utterance (Hinglish)
         │
         ▼
┌─────────────────────┐
│  Language Detection  │  → Detect Hindi/English/Hinglish ratio
│  (langdetect)       │  → Set response language accordingly
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Slot Extractor │  ← The ONLY runtime LLM call
│  (Claude Sonnet)    │  → Extract: field, value, confidence, intent
│  + Rule-based fallback│  → Used when LLM unavailable (offline/CSC)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Contradiction Check │  → Compare new value vs existing ProfileField
│  (Automatic)        │  → Log and escalate if mismatch
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Profile Update FSM │  → Update UserProfile fields
│  (transitions lib)  │  → Move to next priority field
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Rule Engine        │  → run_all_matches() — pure Boolean, no LLM
│  (Pure Python)      │  → gap_analysis()
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Reply Generator    │  → Template-based, NOT LLM
│  (generate_reply()) │  → Based on status + gaps + intent
└────────────────────┘
```

### 2.3 LLM System Prompt (NLU Only)

```python
NLU_SYSTEM_PROMPT = """
You are an NLU slot-extractor for a Hindi/Hinglish government welfare chatbot called KALAM.
Extract structured profile fields from user utterances.
Respond ONLY with valid JSON — no preamble, no explanation, no markdown fences.

CRITICAL RULES:
1. "lagbhag" / "approx" / "around" → set confidence to 0.6 (user_estimated)
2. "shayad" / "maybe" / "nahi pata" → set confidence to 0.3
3. Code-switching is normal — "80 hazaar" = annual_income: 80000
4. "gaon" / "village" / "gramin" → residence_type: "rural"
5. "pati nahi hain" / "husband guzar gaye" → infer marital_status: "widow"
6. "dobaara shaadi" / "naya pati" → remarried: true (CRITICAL for IGNWPS exclusion)
7. "income tax nahi bharta" → income_tax_payer: false
8. "GST file karta hoon" does NOT imply income_tax_payer: true
9. Never infer caste from name or surname — only accept explicit statements

Output Schema:
{
  "extracted_fields": { <field>: <value_or_null> },
  "confidence": { <field>: <0.0-1.0> },
  "intent": "provide_info|ask_scheme|ask_eligibility|ask_documents|grievance|goodbye",
  "follow_up_question": "<next question in Hinglish if needed>"
}
"""
```

### 2.4 Rule-Based Fallback (Offline Mode)

```python
def _rule_based_extract(text: str) -> dict:
    """
    Fallback extractor for offline/CSC environments.
    Uses regex + keyword matching. Less accurate but always available.
    """
    t = text.lower()
    fields = {}

    # State detection
    STATE_MAP = {
        "rajasthan": "Rajasthan", "bihar": "Bihar", "up": "Uttar Pradesh",
        "uttar pradesh": "Uttar Pradesh", "mp": "Madhya Pradesh",
        "madhya pradesh": "Madhya Pradesh", "maharashtra": "Maharashtra",
        "gujarat": "Gujarat", "karnataka": "Karnataka",
        "jharkhand": "Jharkhand", "odisha": "Odisha",
        "chhattisgarh": "Chhattisgarh", "west bengal": "West Bengal",
    }
    for key, val in STATE_MAP.items():
        if key in t: fields["state"] = val; break

    # Residence type
    if any(w in t for w in ["gaon","village","rural","gramin","deh"]):
        fields["residence_type"] = "rural"
    elif any(w in t for w in ["shahar","city","urban","shahr","nagar"]):
        fields["residence_type"] = "urban"

    # Occupation
    if any(w in t for w in ["kisan","farmer","kheti","krishi","fasal"]):
        fields["occupation"] = "farmer"
    elif any(w in t for w in ["mazdoor","labour","worker","mzdur"]):
        fields["occupation"] = "labourer"
    elif any(w in t for w in ["naukri","job","employee","office","sarkari"]):
        fields["occupation"] = "govt_employee" if "sarkari" in t else "private_employee"

    # Marital / Gender
    if any(w in t for w in ["vidhwa","widow","pati nahi","husband nahi","guzar gaye"]):
        fields["marital_status"] = "widow"; fields["gender"] = "female"
    if any(w in t for w in ["dobaara","remarried","dusri shadi","naya pati"]):
        fields["remarried"] = True
    if any(w in t for w in ["mahila","female","aurat"]):
        fields["gender"] = "female"
    elif any(w in t for w in ["purush","male","aadmi","mard"]):
        fields["gender"] = "male"

    # Documents
    if "aadhaar nahi" in t or "no aadhaar" in t:      fields["aadhaar"] = False
    elif "aadhaar" in t and ("hai" in t or "haan" in t): fields["aadhaar"] = True
    if "bank nahi" in t or "account nahi" in t:        fields["bank_account"] = False
    elif "bank" in t and ("hai" in t or "account" in t): fields["bank_account"] = True
    if "bpl" in t and ("hai" in t or "card" in t):    fields["bpl_category"] = True
    if "income tax" in t and ("nahi" in t or "no" in t): fields["income_tax_payer"] = False

    # Numerical parsing
    import re
    age_m = re.search(r"(\d{1,3})\s*(saal|sal|year|yr|age|umar)", t)
    if age_m: fields["age"] = int(age_m.group(1))

    inc_m = re.search(r"(\d[\d,]*)\s*(hazaar|lakh|k|thousand|L)?", t)
    if inc_m:
        num = int(inc_m.group(1).replace(",",""))
        unit = (inc_m.group(2) or "").lower()
        if unit in ("hazaar","thousand","k"):  num *= 1000
        if unit in ("lakh","l"):               num *= 100000
        if 1000 <= num <= 5000000:
            fields["annual_income"] = num

    intent = "provide_info"
    if any(w in t for w in ["kya milega","scheme","yojana","batao","list"]): intent = "ask_scheme"
    if any(w in t for w in ["eligible","qualify","milega","apply"]): intent = "ask_eligibility"
    if any(w in t for w in ["document","kagaz","cert","proof"]): intent = "ask_documents"
    if any(w in t for w in ["shukriya","thanks","bye","dhanyawad","bas"]): intent = "goodbye"

    return {
        "extracted_fields": fields,
        "confidence": {k: (0.85 if k != "annual_income" else 0.7) for k in fields},
        "intent": intent,
        "follow_up_question": "",
    }
```

---

## 3. Conversation Flows (State Machine)

### 3.1 FSM States

```
STATES:
  GREETING          → Initial welcome, ask state
  COLLECTING        → Gathering profile fields (sequential per FIELD_PRIORITY_ORDER)
  CONTRADICTION     → Detected conflicting data — ask user to clarify
  MATCHING          → Profile ≥40% complete — show results
  GAP_DRILL_DOWN    → User asks about specific missing field
  ESCALATE          → Cannot determine — refer to human officer
  FAREWELL          → Conversation end

TRANSITIONS:
  GREETING      → COLLECTING      (user responds with any info)
  COLLECTING    → CONTRADICTION   (new value conflicts with existing)
  COLLECTING    → MATCHING        (profile_completion_pct >= 40%)
  MATCHING      → GAP_DRILL_DOWN  (user asks "mutation ke baare mein?")
  MATCHING      → ESCALATE        (confidence < 0.30 on all schemes)
  CONTRADICTION → COLLECTING      (user clarifies)
  ANY           → FAREWELL        (intent == "goodbye")
```

### 3.2 Contradiction Handler

```python
def handle_contradiction(profile: UserProfile, field: str, new_value, context_msg: str) -> str:
    """
    Called when user provides a value that conflicts with a previously stated one.
    Does NOT auto-update — presents the conflict explicitly and asks for confirmation.
    """
    pf = getattr(profile, field)
    old_val = pf.value

    # Special case: Widow → Remarried (EC-01 pattern)
    if field == "marital_status" and old_val == "widow" and new_value in ("married","remarried"):
        profile.remarried.value = True  # Flag for IGNWPS exclusion
        return (
            f"⚠️  RUKO — Ek important baat:\n\n"
            f"Aapne pehle kaha aap VIDHWA hain.\n"
            f"Abhi aapne '{context_msg}' mention kiya.\n\n"
            f"Kya aapne dobaara shaadi ki hai?"
        )

    # Generic contradiction
    return (
        f"⚠️  Ek confusion hai:\n\n"
        f"Pehle aapne {field.replace('_',' ')} = '{old_val}' bataya tha.\n"
        f"Ab aap '{new_value}' keh rahe hain.\n\n"
        f"Kaun sa sahi hai?\n"
        f"1. {old_val}\n"
        f"2. {new_value}"
    )
```

---

## 4. Example Transcripts

### Transcript 1: Farmer with Incomplete Land Record (MP)

```
════════════════════════════════════════════════════════════════
  KALAM — Sarkar ki Yojanaon ka Saathi  🇮🇳
════════════════════════════════════════════════════════════════

[SYSTEM] Namaste! Main KALAM hoon.
         Pehle — aap kahan se hain?

[USER]   MP se hoon. Sehore district.

[SYSTEM] ✓ Madhya Pradesh, Sehore.
         Gaon mein rehte hain ya shahar mein?

[USER]   Gaon mein. Main kisan hoon.

[SYSTEM] ✓ Rural. ✓ Occupation: Kisan.
         Aapki umar?

[USER]   45 saal.

[SYSTEM] ✓ 45 saal.
         Annual income lagbhag kitni hai?

[USER]   Ek lakh se kam — 80-90 hazaar.

[SYSTEM] ✓ Income: ~₹85,000/year (estimated).
         Aadhaar hai? Bank account hai?

[USER]   Haan dono hain. SBI mein khata hai.

[SYSTEM] ✓ Aadhaar confirmed. ✓ SBI bank account.
         Khet ka maalik hain? 7/12 utara hai aapke naam par?

[USER]   Haan 3 acre zameen hai lekin mutation pending hai kaafi time se.

[SYSTEM] ⚠️  IMPORTANT:
         PM-KISAN ke liye land record mein aapka naam registered hona ZAROORI hai.
         Mutation pending hone se PM-KISAN portal aapko reject kar sakta hai.

         ═══════════════════════════════════
         📊 AAPKE LIYE SCHEME RESULTS:
         ═══════════════════════════════════

         ⚠️  PM-KISAN: REQUIRES VERIFICATION (55%)
            BLOCK: Mutation pending on land record.
            JAISE HI mutation complete ho — turant apply karein.
            ACTION: Patwari office → mutation status check.

         ✅ MGNREGA: LIKELY QUALIFIED (90%)
            100 din kaam ki guarantee. Gram Panchayat mein Job Card lein.

         ✅ PMSBY: QUALIFIED (95%)
            ₹2 lakh accident cover | ₹20/saal. SBI branch mein form maangein.

         ✅ PMJJBY: QUALIFIED (93%)
            ₹2 lakh life cover | ₹436/saal. Same SBI branch visit.

         🔴 Ayushman PMJAY: CANNOT CONFIRM (30%)
            SECC 2011 data par based. pmjay.gov.in ya 14555.

         ════════════════════════════
         📌 PRIORITY ACTION LIST
         ════════════════════════════
         1. Patwari office — mutation status check (PM-KISAN block)
         2. Gram Panchayat — MGNREGA Job Card
         3. SBI Branch — PMSBY + PMJJBY enroll (1 visit mein dono)
         4. pmjay.gov.in — Ayushman check

[USER]   Mutation ke baare mein kya karna chahiye exactly?

[SYSTEM] Mutation ke liye:
         1. Tehsil office — Mutation Application Number lein
         2. MP Bhulekh portal (mpbhulekh.gov.in) par online check karein
         3. Agar 1 saal se zyada pending — tehsildar ko likha hua application dein
         4. Mutation complete hone ke BAAD PM-KISAN apply karein
```

---

### Transcript 2: Widow with Contradictory Marital Status (Rajasthan)

```
[SYSTEM] Namaste! Kahan se hain?

[USER]   Rajasthan. Barmer district.

[SYSTEM] ✓ Rajasthan, Barmer. Gaon ya shahar?

[USER]   Gaon mein.

[SYSTEM] ✓ Rural. Umar?

[USER]   52 saal.

[SYSTEM] ✓ 52 saal. Kya kaam karti hain?

[USER]   Kuch nahi. Ghar par hoon. Pati nahi hain mere.

[SYSTEM] Samajh gaya. Kya aap vidhwa hain?

[USER]   Haan. BPL card bhi hai. Yellow card.

[SYSTEM] ✓ Vidhwa (widow). ✓ BPL confirmed.
         Bank account hai? Aadhaar?

[USER]   Haan, post office mein khata hai. Aadhaar bhi hai.

[SYSTEM] ✓ Post office account. ✓ Aadhaar.
         Pati kab guzre? Death certificate hai?

[USER]   3 saal pehle. Haan certificate hai.

[SYSTEM] ✓ Death certificate available.
         Ghar mein aur kaun hai?

[USER]   Main, meri beti, aur mera naya pati.

[SYSTEM] ⚠️  RUKO — Ek important baat:

         Aapne pehle kaha aap VIDHWA hain.
         Abhi aapne "mera naya pati" kaha.

         Kya aapne dobaara shaadi ki hai?

[USER]   Haan, ek saal pehle. Lekin pension ke liye abhi bhi purana record hai.

[SYSTEM] Aapki baat samajh mein aayi.

         ⚠️  IMPORTANT INFORMATION:

         IGNWPS (Widow Pension) sirf UN mahilaon ke liye hai jinki
         marital status VIDHWA hai. Dobaara shaadi ke baad eligibility
         NAHI RAHI — chahe purane records mein kuch bhi likha ho.

         Ye system aapko galat raah nahi dikha sakta.

         🔴 IGNWPS: INELIGIBLE (Remarriage ke baad eligibility samaapt)

         ════════════════════════════════════════
         LEKIN — aapke liye aur options hain:
         ════════════════════════════════════════

         ✅ PMSBY (Accident Cover): ₹2L | ₹20/saal → Post office mein form
         ✅ PDS/NFSA: Yellow ration card renew/update karwate rahein
         🟡 PMJAY: 14555 ya pmjay.gov.in par check karein

[USER]   Toh kya mujhe pension wapas karni hogi?

[SYSTEM] Ye ek sensitive aur legal matter hai.
         Main koi legal advice nahi de sakta.

         Sahi kaam:
         1. Block Development Officer (BDO) se milein
         2. Ya District Social Welfare Office
         3. Apni sthiti honestly batayein

         Aap ghabraayein mat — seedha baat karein. 🙏
```

---

### Transcript Annotation Notes

| Feature Demonstrated | Transcript 1 | Transcript 2 |
|---|---|---|
| Incomplete data handling | ✅ (mutation pending) | — |
| Land record ambiguity flagging | ✅ | — |
| Confidence score display | ✅ | ✅ |
| Contradiction detection | — | ✅ (widow → remarried) |
| Safe failure (no illegal advice) | — | ✅ |
| Gap analysis with actionable steps | ✅ | ✅ |
| Emotional sensitivity | Mild | ✅ High |
| Application sequencing | ✅ | ✅ |

---

## 5. NanoAI-Style Dashboard — Design Spec

### 5.1 Visual Design System

The KALAM web dashboard is built in the **NanoAI design language** — a soft periwinkle-to-teal gradient background with a dark near-black sidebar, purple primary accent, and glass-morphism card components.

```
┌──────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px, #0f0f1a)    │  TOPBAR (full width, frosted)  │
│                             │  [🔍 Search...] [+Session] 🔔🌐│
│  क  KALAM                   │                                │
│     Sarkar ki Yojana Saathi │──────────────────────────────  │
│                             │  HERO: Animated orb + title    │
│  💬 Chat Assistant ←active  │                                │
│  📋 Schemes [15]            │  TABS: Chat|Schemes|Gap|Profile│
│  🔍 Gap Analysis            │                                │
│  👤 My Profile              │  CHAT WINDOW (scrollable)      │
│  📌 Track Applications      │  [Bot bubble] [User bubble]    │
│                             │  [typing indicator...]         │
│  ⚙️  Settings               │                                │
│  💡 Send Feedback           │  QUICK ACTION PILLS            │
│  🙏 Help & Support          │  [Kisan Yojana][Widow][PMJAY]  │
│                             │                                │
│  ─────────────────────────  │  STAT CARDS (2x2 grid)         │
│  📱 Download Android        │  [Schemes: 4] [Profile: 44%]   │
│  🍎 Download iOS            │  [Missing: 2] [Turns: 3]       │
│  💬 Open in WhatsApp        │                                │
│                             │  SCHEMES GRID (8 cards)        │
│                             │  [🌾PM-KISAN][⛏MGNREGA]...    │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Component Specifications

| Component | Class | Key CSS | Behavior |
|---|---|---|---|
| Sidebar | `.sidebar` | `width:240px; background:#0f0f1a` | Fixed; nav items highlight on click |
| Hero Orb | `.hero-orb` | `conic-gradient + hue-rotate 8s` | Continuous rotation animation |
| Tab Bar | `.tab` / `.tab.active` | `border-radius:14px; min-width:80px` | Click switches active panel |
| Chat Bubble | `.msg-bubble` | `max-width:72%; border-radius:14px` | Fade-in animation on each message |
| Confidence Bar | `.confidence-fill` | `transition:width 0.8s ease` | Animated fill, color-coded by score |
| Scheme Card | `.scheme-card` | `hover: translateY(-3px)` | Click opens scheme detail |
| Gap Item | `.gap-item` | `border-left-color by priority` | Sorted high→medium→low |
| Stat Card | `.stat-card` | First card: gradient accent | Live updates on profile change |

### 5.3 Confidence Color Coding

```
Confidence ≥ 80% → Green gradient  (#00d4aa → #11998e)  → "Qualified" / "Likely Qualified"
Confidence 50-79% → Orange gradient (#ffa94d → #ff6b35)  → "Requires Verification"
Confidence < 50%  → Pink gradient   (#ff4dab → #c2185b)  → "Ambiguous" / "Ineligible"
```

### 5.4 Animation System

```css
/* Page load — staggered reveal */
.stagger > *:nth-child(n) { animation-delay: 0.05s * n; }

/* Message entrance */
@keyframes msg-in { from { opacity:0; transform:translateY(8px) } to { opacity:1; } }

/* Orb rotation */
@keyframes orb-spin { to { filter: hue-rotate(360deg); } }

/* Typing indicator */
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
  40%           { transform: scale(1);   opacity: 1;   }
}
```

---

## 6. Frontend Component Breakdown

### 6.1 Quick Action Pills

Pre-populated prompts that auto-fill the chat input and trigger `sendMessage()`:

| Pill Label | Injected Message |
|---|---|
| ✨ Kisan Yojana | "Mujhe kisan yojanaon ke baare mein batao" |
| 🌸 Widow Pension | "Widow pension ke liye kya chahiye?" |
| 🏥 Check PMJAY | "Ayushman Bharat ka status check karo" |
| 🆔 Aadhaar Help | "Mera Aadhaar nahi hai kya karein?" |
| 🏦 Jan Dhan | "Bank account nahi hai — Jan Dhan kaise kholein?" |

### 6.2 Stat Cards (Live Updates)

| Card | ID | Updates When |
|---|---|---|
| Schemes Matched | `#matched-count` | Scheme results returned |
| Profile Completion | `#profile-pct` | Any profile field extracted |
| Missing Documents | `#missing-docs` | Gap analysis updated |
| Conversation Turns | `#turn-count` | Each message sent |

### 6.3 Panel Render Functions

```javascript
// Schemes Panel — renders all 15 with confidence bars
function renderSchemes() {
    SCHEMES.map(s => `
        <div class="gap-item">
            <div class="s-icon">${s.icon}</div>
            <div class="gap-content">
                <div class="gap-field">${s.name}</div>
                <div class="confidence-bar">
                    <div class="confidence-fill ${colorClass}" style="width:${pct}%"></div>
                </div>
            </div>
            <div class="gap-priority">${pct}%</div>
        </div>
    `)
}

// Gap Panel — sorted high/medium/low priority
function renderGaps() {
    GAPS.map(g => `
        <div class="gap-item gap-${g.priority}">
            <div class="gap-dot"></div>
            <div class="gap-field">${g.field}</div>
            <div class="gap-action">${g.action}</div>
            <div class="gap-affects">Affects: ${g.affects}</div>
            <div class="gap-priority pri-${g.priority}">${g.priority}</div>
        </div>
    `)
}
```

---

## 7. API Integration Layer

### 7.1 Frontend → Backend Connection

```javascript
// Production: replace with actual FastAPI URL
const API_BASE = 'http://localhost:8000';
let SESSION_ID = null;

async function sendToAPI(message) {
    const resp = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: SESSION_ID,
            message: message,
            channel: 'web'
        })
    });
    const data = await resp.json();
    SESSION_ID = data.session_id;  // Persist across turns

    // Update UI from response
    updateStatCards(data);
    renderSchemeResults(data.scheme_matches);
    renderGapAnalysis(data.gap_analysis);
    return data.reply;
}

function updateStatCards(data) {
    const qualified = data.scheme_matches.filter(
        m => ['QUALIFIED','LIKELY_QUALIFIED'].includes(m.status)
    ).length;
    document.getElementById('matched-count').textContent = qualified || '—';
    document.getElementById('profile-pct').textContent   = data.profile_completion_pct + '%';
    document.getElementById('missing-docs').textContent  = data.gap_analysis.filter(g => g.priority === 'high').length || '—';
    document.getElementById('turn-count').textContent    = data.turn_count;
}
```

### 7.2 WhatsApp Integration (Twilio Webhook)

```python
from fastapi import Request
from twilio.twiml.messaging_response import MessagingResponse

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    from_number = form_data.get("From", "").replace("whatsapp:","")
    body        = form_data.get("Body", "").strip()

    session_id = f"wa_{from_number.replace('+','').replace(' ','_')}"

    # Same chat endpoint — channel differentiation only
    chat_req = ChatRequest(session_id=session_id, message=body, channel="whatsapp")
    response = await chat(chat_req)

    twiml = MessagingResponse()
    twiml.message(response.reply[:1600])  # WhatsApp 1600 char limit
    return Response(content=str(twiml), media_type="application/xml")
```

---

*End of File 2 — Frontend & Conversational UI (v2.0)*
*Next: `3_mistake_analysis_and_edge_cases.md`*