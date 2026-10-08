.PHONY: install seed ingest run-agent run-agent-fast run-api run-web test demo

VENV := .venv
PY := $(VENV)/bin/python

install:  ## one-time setup: venv + editable installs + web deps
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e packages/core
	$(PY) -m pip install -e services/agent
	$(PY) -m pip install -e services/api
	$(PY) -m pip install pytest
	cd apps/web && npm install

seed:  ## reset db and load pre-aged demo loops
	$(PY) demo/seed.py

ingest:  ## extract loops from demo/transcripts (skips meetings already ingested)
	$(PY) -m latch_agent.ingest.file_adapter demo/transcripts

run-agent:  ## scheduler: adjudicate new replies, chase overdue loops
	$(PY) -m latch_agent.scheduler

run-agent-fast:  ## same, compressed clock for recording
	$(PY) -m latch_agent.scheduler --fast

run-api:  ## FastAPI backend at localhost:8000
	$(PY) -m uvicorn latch_api.main:app --reload --port 8000

run-web:  ## React UI at localhost:5173 (proxies /api to run-api)
	cd apps/web && npm run dev

test:  ## run pytest
	$(PY) -m pytest tests/

demo: seed ingest  ## put the whole system into a known state for recording
	$(MAKE) run-agent-fast &
	$(MAKE) run-api &
	$(MAKE) run-web
