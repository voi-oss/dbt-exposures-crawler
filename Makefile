.PHONY: type
type:
	@echo "Running mypy"
	@pipenv run mypy src/

.PHONY: lint
lint:
	@echo "Running black"
	@pipenv run black .
	@echo "Running flake"
	@pipenv run flake8

.PHONY: test
test:
	@echo "Running pytest"
	@pipenv run pytest

.PHONY: ci
ci: type lint test