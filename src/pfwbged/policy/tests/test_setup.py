# -*- coding: utf-8 -*-
"""Setup/installation tests for this package."""

from pfwbged.policy.testing import IntegrationTestCase
from plone import api


class TestInstall(IntegrationTestCase):
    """Test installation of pfwbged.policy into Plone."""

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if pfwbged.policy is installed with portal_quickinstaller."""
        self.assertTrue(self.installer.isProductInstalled('pfwbged.policy'))

    def test_uninstall(self):
        """Test if pfwbged.policy is cleanly uninstalled."""
        self.installer.uninstallProducts(['pfwbged.policy'])
        self.assertFalse(self.installer.isProductInstalled('pfwbged.policy'))
