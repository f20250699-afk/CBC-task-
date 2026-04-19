import os
import json
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# Use SambaNova, Anthropic or Standard OpenAI endpoints.
# This assumes the user provides an OpenAI-compatible API proxy/key via .env
api_key = os.getenv("LLM_API_KEY", "dummy-key")
base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1") 
model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")

client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url if base_url else None
)

NLU_SYSTEM_PROMPT = """
You are an NLU slot-extractor for a Hindi/Hinglish government welfare chatbot called KALAM.
Extract structured profile fields from user utterances.
Respond ONLY with valid JSON — no preamble, no explanation, no markdown fences.

CRITICAL RULES:
1. "lagbhag" / "approx" / "around" → set confidence to 0.6 (user_estimated)
2. "shayad" / "maybe" / "nahi pata" → set confidence to 0.3
3. Code-switching is normal — "80 hazaar" = annual_household_income: 80000
4. "gaon" / "village" / "gramin" → residence_type: "rural"
5. "pati nahi hain" / "husband guzar gaye" → infer marital_status: "widow"
6. "dobaara shaadi" / "naya pati" → remarried: true (CRITICAL for IGNWPS exclusion)
7. "income tax nahi bharta" → income_tax_payer: false
8. "GST file karta hoon" does NOT imply income_tax_payer: true
9. Never infer caste from name or surname — only accept explicit statements

Output Schema STRICTLY (JSON Only):
{
  "extracted_fields": {
    "name": null,
    "age": null,
    "gender": null,
    "state": null,
    "residence_type": null,
    "annual_household_income": null,
    "occupation": null,
    "land_ownership_status": null,
    "marital_status": null,
    "bank_account_linked_aadhaar": null,
    "secc_2011_listed": null,
    "housing_status": null,
    "income_tax_payer": null,
    "remarried": null
  },
  "confidence": { "example_field": 0.8 },
  "intent": "provide_info|ask_scheme|ask_eligibility|ask_documents|grievance|goodbye",
  "follow_up_question": ""
}
"""

def fallback_extract(text: str) -> dict:
    t = text.lower()
    fields = {}

    STATE_MAP = {
        "rajasthan": "Rajasthan", "bihar": "Bihar", "up": "Uttar Pradesh",
        "uttar pradesh": "Uttar Pradesh", "mp": "Madhya Pradesh",
        "madhya pradesh": "Madhya Pradesh", "maharashtra": "Maharashtra",
        "jharkhand": "Jharkhand", "odisha": "Odisha",
    }
    for key, val in STATE_MAP.items():
        if key in t: fields["state"] = val; break

    if any(w in t for w in ["gaon","village","rural","gramin"]):
        fields["residence_type"] = "rural"
    elif any(w in t for w in ["shahar","city","urban","nagar"]):
        fields["residence_type"] = "urban"

    if any(w in t for w in ["kisan","farmer","krishi"]):
        fields["occupation"] = "farmer"
    elif any(w in t for w in ["mazdoor","labour"]):
        fields["occupation"] = "labourer"

    if any(w in t for w in ["vidhwa","widow"]):
        fields["marital_status"] = "widow"; fields["gender"] = "female"
    if any(w in t for w in ["dobaara","remarried"]):
        fields["remarried"] = True

    # Hinglish Name extraction
    import re
    # Covers: "mera naam aamir hai", "aamir naam hai", "mai aamir hu"
    name_match = re.search(r'(?:mera\s+naam\s+)?([a-z]+)\s+(?:naam\s+hai|hu|hoon)', t)
    if name_match:
        fields["name"] = name_match.group(1).capitalize()

    # Simple age extraction (looks for the first number)
    import re
    nums = re.findall(r'\d+', t)
    if nums:
        # If it's a reasonable age number
        age_candidate = int(nums[0])
        if 5 < age_candidate < 110:
            fields["age"] = age_candidate

    intent = "provide_info"
    if any(w in t for w in ["shukriya","thanks","bye"]): intent = "goodbye"

    return {
        "extracted_fields": fields,
        "confidence": {k: 0.8 for k in fields},
        "intent": intent,
        "follow_up_question": ""
    }

async def extract_slots(text: str) -> dict:
    try:
        if api_key == "dummy-key":
            logger.warning("LLM_API_KEY not set. Using rule-based fallback.")
            return fallback_extract(text)

        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": NLU_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"LLM Extraction failed: {e}. Using fallback.")
        return fallback_extract(text)
