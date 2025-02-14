# Include variables
include config.mk


## install	: Install the package
.PHONY: install
install :
	$(PIP) install .


## develop 	: Install the package in development mode
.PHONY: develop
develop :
	$(PIP) install -e .


## env		: Prepare a virtual environment to run the package
.PHONY: env
env : $(ENV)/.touchfile
	@echo "The environment ($(ENV)) is up to date."


# Create/update the virtual environment (based on `requirements.txt`, etc.)
# Uses touchfile as proxy for installed environment
$(ENV)/.touchfile : $(REQS) pyproject.toml
	@echo "Installing/updating the environment ($(ENV))."
	@if [ ! -d "$(ENV)" ]; then $(PYTHON) -m venv $(ENV); fi
	@. $(ENV_ACTIVATE); \
	$(PIP) install -r $(REQS) -e .
	@touch $(ENV)/.touchfile


## docs 		: Build documentation
.PHONY: docs
docs : env
	@rm -rf $(DOCS_SRC_API)
	@. $(ENV_ACTIVATE); \
	sphinx-apidoc -f -o $(DOCS_SRC_API) $(PACKAGE_DIR); \
	sphinx-build -b html $(DOCS_SRC) $(DOCS_HTML)


## test		: Run tests
.PHONY: test
test : env
	@. $(ENV_ACTIVATE); \
	pytest $(COVERAGE_OPTIONS) \
		--cov-report term \
		--cov-report html


## format		: Format the package source code
.PHONY: format
format : env $(PYTHON_FORMAT_FILES)
	@. $(ENV_ACTIVATE); \
	isort $(PYTHON_FORMAT_FILES); \
	black $(PYTHON_FORMAT_FILES)


## format-diff	: See the differences that will be produced by formatting
.PHONY: format-diff
format-diff : env $(PYTHON_FORMAT_FILES)
	@. $(ENV_ACTIVATE); \
	isort --diff --color $(PYTHON_FORMAT_FILES); \
	black --diff --color $(PYTHON_FORMAT_FILES)


## package	: Bundle the package for distribution
.PHONY: package
package : env
	@. $(ENV_ACTIVATE); \
	hatch build


## upload		: Upload the package to PyPI
.PHONY: upload
upload : env
	@. $(ENV_ACTIVATE); \
	hatch publish --user __token__ --auth $$(cat .TOKEN)


## clean		: Clean all automatically generated files
.PHONY : clean
clean :
	@rm -rf $(PACKAGE_DIR)/_version.py
	@rm -rf htmlcov/
	@rm -rf dist/ *egg-info/
	@rm -rf .pytest_cache/
	@rm -rf $(DOCS_SRC_API)
	@rm -rf $(ENV)


.PHONY: help
help : Makefile
	@sed -n 's/^##//p' $<
