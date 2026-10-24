# Targets owned by M4: install, api, test-contract, test-planner.
# Other members add theirs (data, demo, test, test-full, web, dev, ...).
# Activate the virtualenv first, or pass PYTHON=.venv/Scripts/python (Windows).
PYTHON ?= python

.PHONY: install api test-contract test-planner

install:
	$(PYTHON) -m pip install -e ".[dev]"

api:
	$(PYTHON) -m uvicorn api.main:app --reload --port 8000

test-contract:
	$(PYTHON) -m pytest tests/contract

test-planner:
	$(PYTHON) -m pytest tests/unit tests/property
