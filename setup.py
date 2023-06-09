# -*- coding: utf-8 -*-
"""Installer for the pfwbged.policy package."""

from setuptools import find_packages
from setuptools import setup


long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')


setup(
    name='pfwbged.policy',
    version='1.0',
    description="Policy package for PFWB GED project",
    long_description=long_description,
    # Get more from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 4.2",
        "Framework :: Plone :: 4.3",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
    ],
    keywords='pfwb,ged,policy',
    author='Cédric Messiant',
    author_email='cedricmessiant@ecreall.com',
    url='http://pypi.python.org/pypi/pfwbged.policy',
    license='GPL',
    packages=find_packages('src', exclude=['ez_setup']),
    namespace_packages=['pfwbged'],
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'collective.contact.core',
        'collective.dms.basecontent',
        'collective.dms.batchimport',
        'collective.dms.mailcontent',
        'collective.documentviewer',
        'collective.edm.listing',
        'collective.externaleditor',
        'collective.onlogin',
        'collective.select2',
        'collective.solr',
        'collective.task',
        'collective.taskqueue',
        'five.grok',
        'pfwbged.basecontent',
        'pfwbged.collection',
        'pfwbged.contact',
        'pfwbged.theme',
        'pfwbged.folder',
        'plone.app.contenttypes',
        'z3c.jbot',
        'Products.AROfficeTransforms',
        'collective.impersonate',
    ],
    extras_require={
        'test': [
            'ecreall.helpers.testing',
            'plone.app.robotframework',
            'plone.app.testing',
        ],
    },
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
