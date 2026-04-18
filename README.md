# KALAM | Welfare Eligibility System

**KALAM** is a deterministic rules engine and conversational AI system designed to help beneficiaries in India identify government welfare schemes they are eligible for. The system uses a "Hinglish" NLU layer to extract user profile details and evaluates them against 15+ central government schemes with an auditable logic trail.

## Key Features
- **Deterministic Rules Engine**: No black-box inference. Every eligibility result is traceable to official gazette notifications.
- **Hinglish NLU Layer**: Handles code-switching (Hindi + English) and informal inputs common in rural contexts.
- **Ambiguity Mapping**: Detects and flags complex eligibility scenarios (e.g., land record mutation pending).
- **NanoAI-Style Dashboard**: A premium, responsive web interface modeled after modern AI dashboards.

## Project Structure
- `index.html`: The main web dashboard (Static frontend).
- `1_backend_and_architecture.md`: Detailed documentation of the FastAPI backend and system logic.
- `frontend.md`: Design specifications and UI/UX architecture.
- `3_mistake_analysis_and_edge_cases.md`: Adversarial testing logs and production-readiness analysis.

## Getting Started

### 1. Frontend (Web Dashboard)
The primary interface is a standalone static HTML file. You can run it by opening `index.html` in any modern web browser.
- **Zero Dependencies**: Works offline and can be deployed from a USB drive or any static host.

### 2. Backend (FastAPI)
The project documentation includes a comprehensive FastAPI implementation for the NLU and Matching Engine.
- **Installation**:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install fastapi uvicorn pydantic anthropic redis networkx
  ```
- **Configuration**:
  Set your API keys as environment variables:
  ```bash
  export ANTHROPIC_API_KEY="YOUR_API_KEY"
  ```
- **Execution**:
  ```bash
  uvicorn app:app --reload --port 8000
  ```

## Testing & Validation
The system has been validated against 10 critical adversarial edge cases, including:
- Remarried widows (categorical exclusion check).
- Lessee farmers (land ownership ambiguity).
- Migrant workers (cross-state documentation verification).

Refer to `3_mistake_analysis_and_edge_cases.md` for the full audit trail.

## License
MIT License
