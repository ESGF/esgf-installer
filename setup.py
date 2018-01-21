# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='esgf-installer',
    version='v2.4.0-devel-release',
    description='Installer for the ESGF Software Package',
    long_description=readme,
    author='William Hill',
    author_email='hill119@llnl.gov',
    url='https://github.com/ESGF/esgf-installer',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)