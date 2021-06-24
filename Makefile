.PHONY: type
type:
	@echo "Running mypy"
	@mypy src/

.PHONY: lint
lint:
	@echo "Running black"
	@black .
	@echo "Running flake"
	@flake8

.PHONY: test
test:
	@echo "Running pytest"
	@pytest

.PHONY: ci
ci: type lint test