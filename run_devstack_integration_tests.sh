#!/bin/bash
set -e

source /edx/app/edxapp/venvs/edxapp/bin/activate

cd /edx/app/edxapp/edx-platform
mkdir -p reports

pip install -r ./requirements/edx/testing.txt

pip install -e .

cd /edx/src/rapid-response-xblock
pip install -e .

# Install codecov so we can upload code coverage results
pip install codecov

# output the packages which are installed for logging
pip freeze

mkdir -p test_root  # for edx

set +e

# We're running pycodestyle directly here since pytest-pep8 hasn't been updated in a while and has a bug
# linting this project's code. pylint is also run directly since it seems cleaner to run them both
# separately than to run one as a plugin and one by itself.
pytest tests --cov .
PYTEST_SUCCESS=$?
pycodestyle rapid_response_xblock tests
PYCODESTYLE_SUCCESS=$?
(cd /edx/app/edxapp/edx-platform; pylint /edx/src/rapid-response-xblock/rapid_response_xblock /edx/src/rapid-response-xblock/tests)
PYLINT_SUCCESS=$?

if [[ $PYTEST_SUCCESS -ne 0 ]]
then
    echo "pytest exited with a non-zero status"
    exit $PYTEST_SUCCESS
fi
if [[ $PYCODESTYLE_SUCCESS -ne 0 ]]
then
    echo "pycodestyle exited with a non-zero status"
    exit $PYCODESTYLE_SUCCESS
fi
if [[ $PYLINT_SUCCESS -ne 0 ]]
then
    echo "pylint exited with a non-zero status"
    exit $PYLINT_SUCCESS
fi

set -e
coverage xml
