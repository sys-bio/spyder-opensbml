# -*- coding: utf-8 -*-
"""
Setup script for spyder_opensbml
"""

from setuptools import setup, find_packages
import os
import os.path as osp

def get_readme():
    with open('README.md') as f:
        readme = str(f.read())
    return readme

# Requirements
REQUIREMENTS = ['tellurium']

setup(
    name='spyder_opensbml',
    version='1.0.0',
    packages=['spyder_opensbml'],
    keywords=["Qt PyQt4 PyQt5 PySide spyder plugins spyplugins systems-biology"],
    #install_requires=REQUIREMENTS,
    url='https://github.com/kirichoi/spyder-opensbml',
    license='MIT',
    author='Kiri Choi',
    author_email='',
    maintainer='Sauro Lab',
    maintainer_email='',
    description='openSBML plugin for Spyder 3.0+',
    long_description=get_readme(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Environment :: Win32 (MS Windows)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Widget Sets'],
    zip_safe=False
    )
    