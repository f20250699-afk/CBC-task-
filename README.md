# KALAM | Welfare Eligibility System

**KALAM** is a deterministic rules engine and conversational AI system designed to help beneficiaries in India identify government welfare schemes they are eligible for. The system uses a "Hinglish" NLU layer to extract user profile details and evaluates them against 12+ central government schemes with an auditable logic trail.

## Key Features
- **Deterministic Rules Engine**: No black-box inference. Every eligibility result is traceable to official gazette notifications.
- **Vibrant Government UI**: A clean, accessible light-mode interface specifically designed with coral/orange accenting, responsive touchbar suggestion pills, and real-time gap analysis.
- **Hinglish NLU Layer**: Handles code-switching (Hindi + English) and informal inputs common in rural contexts (e.g., "Aamir naam hai", "mai 34 saal ka hu").
- **Anti-Loop Dialogue Manager**: Proactively tracks dialogue state. If a user provides an unexpected response or the AI is rate-limited, the robust fallback engine captures raw input to ensure the user is *never* asked the same question twice.

## Project Structure
- `frontend/`: The User Interface (HTML, CSS, JS). Features dynamic touchbars and the vibrant access UI.
- `backend/`: The FastAPI backend containing the Deterministic Rules Engine, Models, and LLM NLU layer.
- `1_backend_and_architecture.md`: Detailed documentation of the backend architecture.
- `frontend.md`: Design specifications and UI/UX architecture.
- `3_mistake_analysis_and_edge_cases.md`: Adversarial testing logs and production-readiness analysis.

## Getting Started

You will need to start both the Python backend API and the local Web Server for the frontend. **Two terminal windows are required.**

### 1. Backend (FastAPI + LLM NLU)
The backend requires an OpenAI-compatible API key (SambaNova, OpenAI, Anthropic, etc).
- **Setup & Installation**:
  ```bash
  cd backend
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  cp .env.example .env
  ```
- **Configuration**:
  Edit the `backend/.env` file with your specific `LLM_API_KEY` and `LLM_BASE_URL` (SambaNova example is inside).
- **Execution**:
  ```bash
  # Inside backend folder with venv activated
  uvicorn main:app --reload --port 8000
  ```

### 2. Frontend (Web Dashboard)
The frontend communicates directly with `localhost:8000`.
- **Execution**:
  ```bash
  cd frontend
  python3 -m http.server 3000
  ```
  Then visit `http://localhost:3000` in your browser.

## Testing & Validation
The system has been validated against critical adversarial edge cases, including:
- Name and Age extraction against heavy API rate-limiting via Regex injection fallbacks.
- Remarried widows (categorical exclusion check).
- Lessee farmers (land ownership ambiguity).
- Non-standard inputs triggering the conversational Anti-Loop mechanic.

Refer to `3_mistake_analysis_and_edge_cases.md` for the original audit trail prior to UI overhauls.

## License
MIT License
