from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import time
from dotenv import load_dotenv

import models
from models import UserProfile, ChatRequest, ChatResponse, ProfileField, DataSource
import nlu
import schemes_db
from rule_engine import match_scheme, do_gap_analysis

load_dotenv()

app = FastAPI(title="KALAM Welfare Eligibility API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for demo. Production should use Redis.
SESSIONS = {}

def get_or_create_session(session_id: str = None) -> UserProfile:
    if not session_id or session_id not in SESSIONS:
        session_id = session_id or str(uuid.uuid4())
        SESSIONS[session_id] = UserProfile(session_id=session_id)
    return SESSIONS[session_id]

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    profile = get_or_create_session(request.session_id)
    profile.channel = request.channel
    profile.turn_count += 1
    
    # 1. NLU Extraction
    nlu_res = await nlu.extract_slots(request.message)
    fields = nlu_res.get("extracted_fields", {})
    confidences = nlu_res.get("confidence", {})
    
    contradictions = []
    
    # 2. Update Profile & Detect Contradictions
    for fname, new_val in fields.items():
        if new_val is not None and hasattr(profile, fname):
            # Contradiction detection
            pf = getattr(profile, fname)
            old_val = pf.value
            
            # Widow remarriage special case
            if fname == "marital_status" and old_val == "widow" and new_val in ["married", "remarried"]:
                profile.remarried.value = True
                contradictions.append(f"Aapne pehle kaha aap VIDHWA hain. Abhi '{new_val}' mention kiya.")
                continue

            if old_val is not None and str(old_val).lower() != str(new_val).lower() and fname != "remarried":
                contradictions.append(f"Pehle aapne {fname} = '{old_val}' bataya, ab '{new_val}'. Kon sa sahi hai?")
                continue
            
            conf = confidences.get(fname, 1.0)
            setattr(profile, fname, ProfileField(
                value=new_val,
                source=DataSource.USER_STATED,
                confidence=conf,
                raw_utterance=request.message,
                turn_number=profile.turn_count
            ))

    # 3. Save session
    profile.last_updated_at = time.time()
    SESSIONS[profile.session_id] = profile

    # 4. Generate Reply and Matching
    if contradictions:
        reply = "\n".join(["⚠️ EK CONFUSION HAI:"] + contradictions)
        matches = []
        gaps = []
    else:
        matches = [match_scheme(sch, profile) for sch in schemes_db.SCHEMES]
        gaps = do_gap_analysis(matches)
        
        # Simple reply generator
        reply = "Samajh gaya. "
        extracted_names = [f for f, v in fields.items() if v is not None]
        if extracted_names:
            reply += f"Maine aapki details ({', '.join(extracted_names)}) update kar di hain. "
            
        if profile.completion_pct() < 40:
             reply += getattr(nlu_res, "follow_up_question", "Kripya apne baare mein aur batayein (Age, kaam, state).")
        else:
             reply += "Aapki eligibility niche update kar di gayi hai."

    return ChatResponse(
        session_id=profile.session_id,
        reply=reply,
        profile_snapshot=profile.to_flat_dict(),
        scheme_matches=matches,
        gap_analysis=gaps,
        turn_count=profile.turn_count,
        profile_completion_pct=profile.completion_pct()
    )

@app.get("/init", response_model=ChatResponse)
async def init_endpoint():
    profile = get_or_create_session(None)
    matches = [match_scheme(sch, profile) for sch in schemes_db.SCHEMES]
    gaps = do_gap_analysis(matches)
    
    return ChatResponse(
        session_id=profile.session_id,
        reply="",
        profile_snapshot=profile.to_flat_dict(),
        scheme_matches=matches,
        gap_analysis=gaps,
        turn_count=profile.turn_count,
        profile_completion_pct=profile.completion_pct()
    )

@app.get("/health")
def health_check():

    return {"status": "ok", "sessions_active": len(SESSIONS)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
