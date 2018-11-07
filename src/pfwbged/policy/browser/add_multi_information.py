from copy import deepcopy
import z3c.form
from z3c.form import button

import zope.event
from zope.i18nmessageid.message import MessageFactory

from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.utils import createContentInContainer
from plone.stringinterp.adapters import _recursiveGetMembersFromIds

from collective.task import _


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
            base_document = api.content.get(str(document_id))
            self.add_info(base_document, data)

        self._finishedAdd = True
        return

    def add_info(self, base_document, data):
        portal = api.portal.get()
        objs = []
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

        print 'seen:', seen
