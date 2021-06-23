.PHONY: test
test:
	pytest

.PHONY: lint
lint:
	mypy src/
	black .
	flake8