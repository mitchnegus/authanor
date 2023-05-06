# Coverage configuration
PYTHON = python3.9
PIP = $(PYTHON) -m pip
# Package
PACKAGE = authanor
PACKAGE_DIR = src/$(PACKAGE)
PACKAGE_PYTHON_FILES = $(wildcard $(PACKAGE_DIR)/*.py) \
		       $(wildcard $(PACKAGE_DIR)/**/*.py)
# Requirements files
REQS = requirements.txt
# Package environment (for building and testing)
ENV = authanor-env
ENV_BIN = $(ENV)/bin
ENV_ACTIVATE = $(ENV_BIN)/activate

# Documentation locations
DOCS = docs
DOCS_SRC = $(DOCS)/source
DOCS_SRC_API = $(DOCS_SRC)/api
DOCS_BUILD = $(DOCS)/build
DOCS_HTML = $(DOCS_BUILD)/html

# Testing
TEST_DIR = tests
TEST_PYTHON_FILES = $(wildcard $(TEST_DIR)/*.py) \
		    $(wildcard $(TEST_DIR)/**/*.py)
COVERAGE_OPT_LOCATION = --cov=.
COVERAGE_OPTIONS = $(COVERAGE_OPT_LOCATION)

# Format files
PYTHON_FORMAT_FILES = $(PACKAGE_PYTHON_FILES) $(TEST_PYTHON_FILES)
