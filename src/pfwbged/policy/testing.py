# -*- coding: utf-8 -*-
"""Base module for unittesting."""

from plone import api
from plone.app.robotframework.testing import AUTOLOGIN_LIBRARY_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import login
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.testing import z2

import unittest2 as unittest

from ecreall.helpers.testing import member as memberhelpers

from collective.contact.core.setuphandlers import create_test_contact_data
import pfwbged.policy


GROUPDEFS = [{'group': 'chef_info', 'roles': ('',),
              'title': 'Chef du service informatique', 'groups': ()},
             {'group': 'chef_finances', 'roles': ('',),
              'title': 'Chef du service finances', 'groups': ()},
             ]


USERDEFS = [{'user': 'secretaire', 'roles': ('Member', ), 'groups': ()},
            {'user': 'greffier', 'roles': ('Greffier', 'Member', 'Reviewer'),
             'groups': ()},
            {'user': 'editor', 'roles': ('Member', ), 'groups': ()},
            {'user': 'editor2', 'roles': ('Member', ), 'groups': ()},
            {'user': 'editor3', 'roles': ('Member', ), 'groups': ()},
            {'user': 'reader', 'roles': ('Member', ), 'groups': ()},
            {'user': 'manager', 'roles': ('Member', 'Manager'), 'groups': ()},
            # for robot tests
            {'user': 'info', 'roles': ('Member', ), 'groups': ('chef_info',)},
            {'user': 'finances', 'roles': ('Member', ),
             'groups': ('chef_finances',)},
            {'user': 'christine', 'roles': ('Member', ),
             'groups': ('chef_info',)},
            {'user': 'robert', 'roles': ('Member', ), 'groups': ()},
            {'user': 'abdes', 'roles': ('Member', ), 'groups': ()},
            ]


class PfwbgedPolicyLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)
    products = ['collective.task',
                'collective.contact.facetednav',
                'collective.documentviewer',
                'collective.local.workspace',
                'collective.solr',
                'collective.task',
                'collective.z3cform.chosen',
                'eea.facetednavigation',
                'pfwbged.collection',
                'pfwbged.folder',
                'pfwbged.policy',
                'plone.app.locales',
                ]

    def setUpZope(self, app, configurationContext):
        """Set up Zope."""
        # Load ZCML
        self.loadZCML(package=pfwbged.policy,
                      name='testing.zcml')
        for p in self.products:
            z2.installProduct(app, p)

    def setUpPloneSite(self, portal):
        """Set up Plone."""
        # Install into Plone site using portal_setup
        applyProfile(portal, 'pfwbged.policy:default')

        # create users
        memberhelpers.createGroups(portal, GROUPDEFS)
        memberhelpers.createMembers(portal, USERDEFS)

        # Login and create some test content
        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)
        portal.invokeFactory('Folder', 'folder')

        portal.portal_types.directory.global_allow = True
        api.content.delete(obj=portal['annuaire'])
        # create some test contacts
        create_test_contact_data(portal)
        portal.portal_types.directory.global_allow = False

        # Commit so that the test browser sees these objects
        portal.portal_catalog.clearFindAndRebuild()
        import transaction
        transaction.commit()

    def tearDownZope(self, app):
        """Tear down Zope."""
        for p in reversed(self.products):
            z2.uninstallProduct(app, p)


FIXTURE = PfwbgedPolicyLayer(
    name="FIXTURE"
    )


ACCEPTANCE = FunctionalTesting(
    bases=(FIXTURE,
           AUTOLOGIN_LIBRARY_FIXTURE,
           z2.ZSERVER_FIXTURE),
    name="ACCEPTANCE"
    )


INTEGRATION = IntegrationTesting(
    bases=(FIXTURE,),
    name="INTEGRATION"
    )

FUNCTIONAL = FunctionalTesting(
    bases=(FIXTURE,),
    name="FUNCTIONAL"
    )


class IntegrationTestCase(unittest.TestCase):
    """Base class for integration tests."""

    layer = INTEGRATION

    def setUp(self):
        super(IntegrationTestCase, self).setUp()
        self.portal = self.layer['portal']


class FunctionalTestCase(unittest.TestCase):
    """Base class for functional tests."""

    layer = FUNCTIONAL
