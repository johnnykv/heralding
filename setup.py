import multiprocessing
from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

setup(
    name='Beeswarm',
    version='0.1-dev',
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
    dependency_links=[
        'git+https://github.com/rep/hpfeeds.git#egg=hpfeeds-1.0.0',
         # temporary until 14.1.0 is released
        'git+https://github.com/zeromq/pyzmq#egg=pyzmq-14.0.2',
    ],
    install_requires=open('requirements.txt').read().splitlines(),
)
