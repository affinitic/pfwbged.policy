# -*- coding: utf8 -*-

from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog

from five import grok

from plone import api

from collective.dms.basecontent.dmsdocument import IDmsDocument
from collective.dms.mailcontent.dmsmail import IDmsOutgoingMail,\
    IDmsIncomingMail
from collective.dms.basecontent.dmsfile import IDmsFile
from collective.dms.basecontent.dmsfile import IDmsAppendixFile
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


class CanAnswerGenericDocument(grok.View):
    """Guard that check if a document that is not an incoming mail can be
    answered (this will never be true but this allows to share the same
    workflow)"""
    grok.name('can_answer')
    grok.context(IDmsDocument)
    grok.require('zope2.View')

    def render(self):
        return False


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
                roles = api.user.get_roles(user=api.user.get_current(), obj=validation)
                if 'Editor' in roles:
                    return True
        return False


class CanCancelRefusal(grok.View):
    grok.name("can_cancel_refusal")
    grok.context(IDmsFile)
    grok.require('zope2.View')

    def render(self):

        workflow = api.portal.get_tool('portal_workflow')
        with api.env.adopt_user('admin'):
            review_history = workflow.getInfoFor(self.context, 'review_history')
        if not review_history:
            return False
        last_transition = review_history[-1]
        return last_transition.get('action') == 'refuse' and \
            last_transition.get('actor') == api.user.get_current().id


class CanCancelValidation(grok.View):
    grok.name("can_cancel_validation")
    grok.context(IDmsFile)
    grok.require('zope2.View')

    def render(self):

        workflow = api.portal.get_tool('portal_workflow')
        with api.env.adopt_user('admin'):
            review_history = workflow.getInfoFor(self.context, 'review_history')
        if not review_history:
            return False
        last_transition = review_history[-1]
        return last_transition.get('action') == 'validate' and \
            last_transition.get('actor') == api.user.get_current().id


class CanBeTrashedDmsFile(grok.View):
    """"""
    grok.name('can_be_trashed')
    grok.context(IDmsFile)
    grok.require('zope2.View')

    def render(self):
        return getattr(self.context, 'signed', False) and api.content.get_state(self.context) == 'finished'


class CanBeTrashedDmsAppendixFile(grok.View):
    """"""
    grok.name('can_be_trashed')
    grok.context(IDmsAppendixFile)
    grok.require('zope2.View')

    def render(self):
        return api.content.get_state(self.context) == 'published'


class CanReturnToRegisteringOrProcess(grok.View):
    """"""
    grok.name('can_return_to_registering_or_process')
    grok.context(IDmsIncomingMail)
    grok.require('zope2.View')

    def render(self):
        # accept any of these roles
        allowed_roles = {'Reviewer', 'Manager', 'Greffier'}
        user_roles = api.user.get_roles(obj=self.context)
        if allowed_roles.intersection(user_roles):
            return True

        # or this user group
        for group in api.group.get_groups(user=api.user.get_current()):
            if group.id == 'Gestion-secretariat-general':
                return True

        return False
