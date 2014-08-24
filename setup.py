import multiprocessing
from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
import beeswarm

setup(
    name='Beeswarm',
    version=beeswarm.version,
    packages=find_packages(exclude=['bin', 'docs']),
    scripts=['bin/beeswarm'],
    url='https://github.com/honeynet/beeswarm',
    license='GPL 3',
    author='Johnny Vestergaard, The Honeynet Project',
    author_email='jkv@unixcluster.dk',
    include_package_data=True,
    long_description=open('README.rst').read(),
    description='Honeytoken transmission, reception and analysis.',
    test_suite='nose.collector',
    install_requires=open('requirements.txt').read().splitlines(),
)
