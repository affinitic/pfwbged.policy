import pickle
from copy import deepcopy

from Products.Five.browser import BrowserView

import z3c.form
from collective.taskqueue import taskqueue
from z3c.form import button

import zope.event
from zope.component import getUtility
from zope.i18nmessageid.message import MessageFactory

from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.utils import createContentInContainer
from plone.stringinterp.adapters import _recursiveGetMembersFromIds

from collective.task import _



class BackgroundAddInformationView(BrowserView):
    def __call__(self):
        base_document = self.context
        data = pickle.load(self.request.stdin)
        portal = api.portal.get()
        seen = {}

        for responsible in data['responsible']:
            group = api.group.get(responsible)
            if group is not None:
                # responsible is a group, create an Information by user in this group
                groupname = group.getId()
                users = _recursiveGetMembersFromIds(portal, [groupname])
                for user in users:
                    username = user.getId()
                    if username in seen:
                        continue
                    _data = deepcopy(data)
                    _data['responsible'] = [username]
                    createContentInContainer(base_document, 'information', **_data)
                    seen[username] = True
            else:
                # responsible is a user
                if responsible in seen:
                    continue
                _data = deepcopy(data)
                _data['responsible'] = [responsible]
                createContentInContainer(base_document, 'information', **_data)
                seen[responsible] = True


class AddInformation(DefaultAddForm):
    """Custom add information view"""

    portal_type = "information"

    @property
    def action(self):
        return self.request.getURL() + '?documents=' + self.request.documents

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        for document_id in self.request.documents.split(','):
            taskqueue.add(
                '{}/background_add_information'.format(document_id),
                payload=pickle.dumps(data),
            )

        self._finishedAdd = True
        return
