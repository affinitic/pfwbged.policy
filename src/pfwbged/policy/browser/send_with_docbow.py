# -*- encoding: utf-8 -*-

import logging
import urllib

from zope.interface import Interface
from zope import schema

from plone.z3cform.layout import FormWrapper
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from plone import api

class SendWithDocbowView(BrowserView):
    def __call__(self):
        version_url = self.context.absolute_url()
        if 'test.pfwb.be' in version_url:
            docbow = 'https://test-secure.pfwb.be'
        else:
            docbow = 'https://secure.pfwb.be'
        docbow += '/send_file/?url=' + urllib.quote(version_url + '/@@download')
        self.request.response.redirect(docbow)
