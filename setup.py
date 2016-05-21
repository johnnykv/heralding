from ez_setup import use_setuptools
use_setuptools()  # NOQA
from setuptools import setup, find_packages
from heralding import version as heralding_version

setup(
    name='Heralding',
    version=heralding_version,
    packages=find_packages(exclude=['bin', 'docs', '*.pyc']),
    scripts=['bin/heralding'],
    url='https://github.com/johnnykv/heralding',
    license='GPL 3',
    author='Johnny Vestergaard',
    author_email='jkv@unixcluster.dk',
    include_package_data=True,
    long_description=open('README.rst').read(),
    description='Credentials catching honeypot.',
    test_suite='nose.collector',
    install_requires=open('requirements.txt').read(),
    package_data={
        "heralding": ["heralding.yml"],
    },
)
