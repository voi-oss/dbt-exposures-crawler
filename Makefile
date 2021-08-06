.PHONY: build
build: clean-build
	python3 setup.py sdist bdist_wheel

.PHONY: clean-build
clean-build:
	rm -rf build dist

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

.PHONY: test-coverage
test-coverage:
	@echo "Running pytest (with coverage)"
	@pipenv run pytest --cov --cov-report=xml

.PHONY: ci
ci: type lint test