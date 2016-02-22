import multiprocessing
from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
from beeswarm import version as beeswarm_version

setup(
    name='Heralding',
    version=beeswarm_version,
    packages=find_packages(exclude=['bin', 'docs']),
    scripts=['bin/heralding'],
    url='https://github.com/honeynet/heralding',
    license='GPL 3',
    author='Johnny Vestergaard, The Honeynet Project',
    author_email='jkv@unixcluster.dk',
    include_package_data=True,
    long_description=open('README.rst').read(),
    description='Credentials catching honeypot.',
    test_suite='nose.collector',
    install_requires=open('requirements.txt').read().splitlines()[2:],
)
