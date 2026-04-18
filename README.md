# KALAM | Welfare Eligibility System

**KALAM** is a deterministic rules engine and conversational AI system designed to help beneficiaries in India identify government welfare schemes they are eligible for. The system uses a "Hinglish" NLU layer to extract user profile details and evaluates them against 15+ central government schemes with an auditable logic trail.

## Key Features
- **Deterministic Rules Engine**: No black-box inference. Every eligibility result is traceable to official gazette notifications.
- **Hinglish NLU Layer**: Handles code-switching (Hindi + English) and informal inputs common in rural contexts.
- **Ambiguity Mapping**: Detects and flags complex eligibility scenarios (e.g., land record mutation pending).
- **NanoAI-Style Dashboard**: A premium, responsive web interface modeled after modern AI dashboards.

## Project Structure
- `frontend/`: The User Interface (HTML, CSS, JS). Detached from the backend.
- `backend/`: The FastAPI backend containing the Deterministic Rules Engine, Models, and LLM NLU layer.
- `1_backend_and_architecture.md`: Detailed documentation of the backend architecture.
- `frontend.md`: Design specifications and UI/UX architecture.
- `3_mistake_analysis_and_edge_cases.md`: Adversarial testing logs and production-readiness analysis.

## Getting Started

You will need to start both the Python backend API and the local Web Server for the frontend. You need two terminal windows.

### 1. Backend (FastAPI + LLM NLU)
The backend requires an OpenAI-compatible API key (SambaNova, OpenAI, or Anthropic).
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
The system has been validated against 10 critical adversarial edge cases, including:
- Remarried widows (categorical exclusion check).
- Lessee farmers (land ownership ambiguity).
- Migrant workers (cross-state documentation verification).

Refer to `3_mistake_analysis_and_edge_cases.md` for the full audit trail.

## License
MIT License
