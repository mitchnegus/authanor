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
ENV = auth-env
ENV_BIN = $(ENV)/bin
ENV_ACTIVATE = $(ENV_BIN)/activate

# Testing
TEST_DIR = tests
TEST_PYTHON_FILES = $(wildcard $(TEST_DIR)/*.py) \
		    $(wildcard $(TEST_DIR)/**/*.py)
COVERAGE_OPT_LOCATION = --cov=.
COVERAGE_OPT_CONFIG = --cov-config=.coveragerc
COVERAGE_OPTIONS = $(COVERAGE_OPT_LOCATION) $(COVERAGE_OPT_CONFIG)

# Format files
PYTHON_FORMAT_FILES = $(PACKAGE_PYTHON_FILES) $(TEST_PYTHON_FILES)