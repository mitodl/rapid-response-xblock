"""Setup for edx-sga XBlock."""

import os
from setuptools import setup, find_packages

import rapid_response_xblock


def package_data(pkg, root_list):
    """Generic function to find package_data for `pkg` under `root`."""
    data = []
    for root in root_list:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='rapid_response_xblock',
    version=rapid_response_xblock.__version__,
    description='Rapid Response XBlock',
    license='BSD',
    url="https://github.com/mitodl/rapid-response-xblock",
    author="MITx",
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    install_requires=['django>=1.8,<=1.11'],
)
