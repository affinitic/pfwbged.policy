# -*- coding: utf-8 -*-

from Products.Five.browser import BrowserView
from collective.task import _
from collective.taskqueue import taskqueue
from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.utils import createContentInContainer
from z3c.form import button
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid import IIntIds


class BackgroundAddLinkView(BrowserView):
    def __call__(self):
        base_document = self.context
        folder_path = self.request.form['folder']
        portal = api.portal.get()
        folder = portal.restrictedTraverse(folder_path)
        intids = getUtility(IIntIds)
        relation = RelationValue(to_id=intids.getId(folder))

        new_link = createContentInContainer(
            base_document,
            'pfwbgedlink',
            folder=relation,
        )


class AddLinks(DefaultAddForm):
    "Add multiple pfwbgedlinks"

    portal_type = "pfwbgedlink"

    @property
    def label(self):
        return u"Classer dans un dossier"

    @property
    def action(self):
        return self.request.getURL() + '?documents=' + self.request.documents

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        folder_path = data['folder'].absolute_url_path().lstrip("/")

        for document_id in self.request.documents.split(','):
            taskqueue.add(
                '{}/background_add_link'.format(document_id),
                params={'folder': folder_path},
            )

        self._finishedAdd = True
        return
