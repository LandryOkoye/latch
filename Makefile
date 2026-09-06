.PHONY: install seed ingest run-agent run-agent-fast run-ui test demo

VENV := .venv
PY := $(VENV)/bin/python

install:  ## one-time setup: venv + editable installs
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e packages/core
	$(PY) -m pip install -e services/agent
	$(PY) -m pip install -e apps/reviewer

seed:  ## reset db and load pre-aged demo loops
	$(PY) demo/seed.py

ingest:  ## run FileAdapter over demo/transcripts
	$(PY) -m latch_agent.ingest.file_adapter demo/transcripts

run-agent:  ## start the scheduler tick loop
	$(PY) -m latch_agent.scheduler

run-agent-fast:  ## same, compressed clock for recording
	$(PY) -m latch_agent.scheduler --fast

run-ui:  ## streamlit run apps/reviewer
	$(VENV)/bin/streamlit run apps/reviewer/src/latch_reviewer/app.py

test:  ## run pytest
	$(PY) -m pytest tests/

demo: seed ingest  ## put the whole system into a known state for recording
	$(MAKE) run-agent-fast &
	$(MAKE) run-ui
