"""Setup for rapid-response-datastore XBlock."""

from setuptools import setup, find_packages

import rapid_response_xblock


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
    entry_points={
        "lms.djangoapp": [
            "rapid_response_xblock = "
            "rapid_response_xblock.apps:RapidResponseAppConfig"
        ],
        "cms.djangoapp": []
    }
)
