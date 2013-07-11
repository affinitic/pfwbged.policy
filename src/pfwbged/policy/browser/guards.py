from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog

from five import grok

from plone import api

from collective.dms.mailcontent.dmsmail import IDmsOutgoingMail,\
    IDmsIncomingMail
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.task.content.validation import IValidation


class OutgoingMailReadyToSend(grok.View):
    """Guard that returns True if ready to send transition is permitted
    It is permitted if the outgoing mail contains a finalized version note
    """
    grok.name("ready_to_send")
    grok.context(IDmsOutgoingMail)
    grok.require("zope2.View")

    def render(self):
        catalog = api.portal.get_tool('portal_catalog')
        container_path = '/'.join(self.context.getPhysicalPath())
        results = catalog.searchResults({'path': {'query': container_path},
                                         'portal_type': 'dmsmainfile',
                                         'review_state': 'finished'})
        return bool(results)


class CanAnswerIncomingMail(grok.View):
    """Guard that check if the incoming mail can be answered
    (i.e. has an sent related doc)
    """
    grok.name('can_answer')
    grok.context(IDmsIncomingMail)
    grok.require('zope2.View')

    def render(self):
        refs_catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        mail_id = intids.getId(self.context)
        for ref in refs_catalog.findRelations({'to_id': mail_id,
                                               'from_interfaces_flattened': IDmsOutgoingMail}):
            outgoing_mail = ref.from_object
            if api.content.get_state(obj=outgoing_mail) == 'sent':
                return True
        return False


# Version note workflow guards
class NoValidationInProgress(grok.View):
    """Guard that verify that we don't have a validation process in progress"""
    grok.name('no_validation_in_progress')
    grok.context(IDmsFile)
    grok.require('zope2.View')

    def render(self):
        state = api.content.get_state(self.context)
        if state == 'draft':
            # OK if there is no pending or validated version in this document
            catalog = api.portal.get_tool('portal_catalog')
            document = self.context.getParentNode()
            document_path = '/'.join(document.getPhysicalPath())
            brains = catalog.searchResults({'portal_type': 'dmsfile',
                                            'review_state': 'pending'},
                                           path={'query': document_path, 'depth': 1})
            if brains:
                return False
        return True


class CanValidateOrRefuse(grok.View):
    grok.name("can_validate_or_refuse")
    grok.context(IDmsFile)
    grok.require('zope2.View')

    def render(self):
        refs_catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        version_id = intids.getId(self.context)
        # validate or refuse in available transition on validation
        for ref in refs_catalog.findRelations({'to_id': version_id,
                                               'from_interfaces_flattened': IValidation}):
            validation = ref.from_object
            if api.content.get_state(validation) == 'todo':
                if api.user.get_current().getId() == validation.responsible[0]:
                    return True
        return False
