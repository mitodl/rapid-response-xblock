"""Setup for rapid-response XBlock."""

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
    install_requires=[
        'django>=2.2,<3.0',
        'XBlock',
        'xblock-utils',
        'edx-opaque-keys'
    ],
    packages=find_packages(),
    package_data=package_data("rapid_response_xblock", ["static"]),
    entry_points={
        'xblock_asides.v1': [
            'rapid_response_xblock = rapid_response_xblock.block:RapidResponseAside',
        ],
        'lms.djangoapp': [
            'rapid_response_xblock = rapid_response_xblock.apps:RapidResponseAppConfig'
        ],
        'cms.djangoapp': [
            'rapid_response_xblock = rapid_response_xblock.apps:RapidResponseAppConfig'
        ],
    }
)
