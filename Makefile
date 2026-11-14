.PHONY: inventory test-unit compose-config compose-up smoke compose-down evidence

inventory:
	python3 scripts/inventory.py

test-unit:
	python3 -m pytest tests/unit -q

compose-config:
	python3 scripts/compose_config.py --version $${VERSION:-3.5.101}

compose-up:
	@echo "Lifecycle start is intentionally gated until the isolated Compose overlay is implemented."
	@exit 2

smoke:
	@echo "Smoke test is unavailable until an isolated lab stack is running."
	@exit 2

compose-down:
	@echo "No lab services are currently managed by this repository."

evidence:
	python3 scripts/create_evidence.py --scenario "$${SCENARIO:?set SCENARIO}" 
