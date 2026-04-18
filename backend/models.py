from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
from enum import Enum
import time

class DataSource(str, Enum):
    USER_STATED = "user_stated"
    USER_ESTIMATED = "user_estimated"
    SYSTEM_INFERRED = "system_inferred"
    DEFAULT_ASSUMED = "default_assumed"
    UNKNOWN = "unknown"

class ProfileField(BaseModel):
    value: Optional[Any] = None
    source: DataSource = DataSource.UNKNOWN
    confidence: float = 0.0
    raw_utterance: str = ""
    turn_number: int = 0
    contradictions: List[dict] = Field(default_factory=list)

class UserProfile(BaseModel):
    session_id: str
    channel: str = "web"
    language_preference: str = "hinglish"
    
    # Core fields
    name: ProfileField = Field(default_factory=ProfileField)
    age: ProfileField = Field(default_factory=ProfileField)
    gender: ProfileField = Field(default_factory=ProfileField)
    state: ProfileField = Field(default_factory=ProfileField)
    residence_type: ProfileField = Field(default_factory=ProfileField)
    annual_household_income: ProfileField = Field(default_factory=ProfileField)
    occupation: ProfileField = Field(default_factory=ProfileField)
    land_ownership_status: ProfileField = Field(default_factory=ProfileField)
    marital_status: ProfileField = Field(default_factory=ProfileField)
    bank_account_linked_aadhaar: ProfileField = Field(default_factory=ProfileField)
    secc_2011_listed: ProfileField = Field(default_factory=ProfileField)
    housing_status: ProfileField = Field(default_factory=ProfileField)
    income_tax_payer: ProfileField = Field(default_factory=ProfileField)
    remarried: ProfileField = Field(default_factory=ProfileField)

    # Session metadata
    created_at: float = Field(default_factory=time.time)
    last_updated_at: float = Field(default_factory=time.time)
    turn_count: int = 0
    contradiction_log: List[dict] = Field(default_factory=list)

    def to_flat_dict(self) -> dict:
        result = {}
        for fname, fval in self.model_dump().items():
            if isinstance(fval, dict) and 'value' in fval:
                result[fname] = fval.get('value')
                result[f"{fname}_confidence"] = fval.get('confidence', 0.0)
        return result

    def completion_pct(self) -> int:
        PRIORITY = ["age", "state", "occupation", "residence_type", "marital_status", "annual_household_income", "bank_account_linked_aadhaar", "land_ownership_status", "housing_status", "secc_2011_listed"]
        filled = 0
        for f in PRIORITY:
            field = getattr(self, f, None)
            if field and field.value is not None:
                filled += 1
        return round((filled / len(PRIORITY)) * 100)

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    channel: str = "web"

class SchemeMatchResult(BaseModel):
    scheme_id: str
    scheme_name: str
    status: str
    confidence_score: float
    confidence_breakdown: dict
    missing_fields: List[str]
    failed_hard_conditions: List[str]
    triggered_exclusions: List[str]
    ambiguity_flags: List[str]
    application_sequence: List[str] = []
    explanation: str
    benefit_summary: str = ""
    required_docs: List[str] = []
    next_action: str = ""

class GapItem(BaseModel):
    field: str
    priority: str
    affects_schemes: List[str]
    how_to_obtain: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    profile_snapshot: Dict[str, Any]
    scheme_matches: List[SchemeMatchResult]
    gap_analysis: List[GapItem]
    turn_count: int
    profile_completion_pct: int
