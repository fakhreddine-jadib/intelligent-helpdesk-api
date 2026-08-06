# Intelligent Helpdesk — API & ML

Backend and Machine Learning engine for the Intelligent Helpdesk platform:
automatic classification, prioritization and routing of customer support tickets.

**PFA 2025/2026 — ALEXSYS SOLUTIONS**
Engineering degree — Artificial Intelligence & Data

## Stack
- Python 3.12
- Flask (REST API, JWT)
- scikit-learn / XGBoost (ML models)
- MongoDB (persistence)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Structure
| Folder | Content |
|---|---|
| `data/` | Datasets (raw / processed) |
| `notebooks/` | EDA and model training |
| `models/` | Serialized ML models |
| `src/` | Flask application |
| `tests/` | Automated tests |

## Frontend
The Next.js interface lives in a separate repository: `intelligent-helpdesk-web`.