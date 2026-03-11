# LojaSync

Web application for product registration automation and shipment manifest (romaneio) organization.

## Problem Solved
Manual product registration and manifest handling are repetitive, slow, and error-prone.
LojaSync centralizes product operations, automates registration flows, and improves data consistency.

## Core Features
- Product CRUD with business validations
- Bulk actions (category, brand, margin, reorder, merge duplicates, merge grades)
- Manifest import pipeline (upload, extraction, parsing, fallback strategies)
- Grade extraction workflow from invoice/manifest files
- Local automation with PyAutoGUI for ByteEmpresa flow
- Remote automation agents via WebSocket
- Metrics tracking (estimated time saved and typed characters)

## Technical Stack
- Backend: Python, FastAPI, Pydantic
- Frontend: HTML, CSS, JavaScript (vanilla)
- Data: JSON/JSONL persistence layer
- Automation: PyAutoGUI + keyboard-driven workflows
- LLM Pipeline: dedicated service for upload/chat extraction + monitoring proxy

## Architecture Overview
- `engine/webapp/`: main runtime (frontend, backend, automation APIs)
- `engine/LLM3/`: LLM service used by romaneio and grade extraction flows
- `engine/modules/automation/`: ByteEmpresa automation routines
- `engine/modules/core/`: shared runtime utilities
- `engine/modules/parsers/parser_grades.py`: grade extraction parser
- `engine/legacy/`: preserved desktop legacy modules and historical artifacts

## Key Engineering Highlights
- Asynchronous job model for long-running imports/extractions
- Multi-stage parser fallback (structured parse -> line parse -> PDF table parse)
- Real-time UI updates with WebSocket events
- Separation between operational data, business actions, and automation execution
- Remote agent orchestration with ack/result lifecycle

## Run Locally
From `engine/webapp`:

```bat
python launcher.py
```

Default services:
- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8800`
- LLM3: `http://127.0.0.1:8002`
- LLM Monitor: `http://127.0.0.1:5174`

## Portfolio Positioning
This project demonstrates practical software engineering in a real operational context:
- automation architecture
- business rule modeling
- resilient data pipelines
- AI-assisted extraction workflows

If you are a recruiter/hiring manager, see `docs/portfolio/` for concise project and profile summaries.
