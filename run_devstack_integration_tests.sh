#!/bin/bash
set -e

source /edx/app/edxapp/venvs/edxapp/bin/activate

cd /edx/app/edxapp/edx-platform
mkdir -p reports

# these pip install commands are adapted from edx-platform/circle.yml
pip install --exists-action w -r requirements/edx/paver.txt

# Mirror what paver install_prereqs does.
# After a successful build, CircleCI will
# cache the virtualenv at that state, so that
# the next build will not need to install them
# from scratch again.
pip install --exists-action w -r requirements/edx/pre.txt
pip install --exists-action w -r requirements/edx/github.txt
pip install --exists-action w -r requirements/edx/local.txt

# HACK: within base.txt stevedore had a
# dependency on a version range of pbr.
# Install a version which falls within that range.
pip install  --exists-action w pbr==0.9.0
pip install --exists-action w -r requirements/edx/django.txt
pip install --exists-action w -r requirements/edx/base.txt
pip install --exists-action w -r requirements/edx/paver.txt
pip install --exists-action w -r requirements/edx/testing.txt
if [ -e requirements/edx/post.txt ]; then pip install --exists-action w -r requirements/edx/post.txt ; fi

cd /rapid-response-xblock
pip install -e .

# Install codecov so we can upload code coverage results
pip install codecov

# output the packages which are installed for logging
pip freeze

mkdir -p test_root  # for edx

set +e

# We're running pep8 directly here since pytest-pep8 hasn't been updated in a while and has a bug
# linting this project's code. pylint is also run directly since it seems cleaner to run them both
# separately than to run one as a plugin and one by itself.
pytest tests --cov .
PYTEST_SUCCESS=$?
pep8 rapid_response_xblock tests
PEP8_SUCCESS=$?
(cd /edx/app/edxapp/edx-platform; pylint /rapid-response-xblock/rapid_response_xblock /rapid-response-xblock/tests)
PYLINT_SUCCESS=$?

if [[ $PYTEST_SUCCESS -ne 0 ]]
then
    echo "pytest exited with a non-zero status"
    exit $PYTEST_SUCCESS
fi
if [[ $PEP8_SUCCESS -ne 0 ]]
then
    echo "pep8 exited with a non-zero status"
    exit $PEP8_SUCCESS
fi
if [[ $PYLINT_SUCCESS -ne 0 ]]
then
    echo "pylint exited with a non-zero status"
    exit $PYLINT_SUCCESS
fi

set -e
coverage xml
codecov
