# -*- encoding: utf-8 -*-

from datetime import datetime

from zope.interface import Interface
from zope import schema
from zope.component import createObject, queryUtility
from z3c.form import form, button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE

from Acquisition import aq_inner, aq_parent

from zope.annotation.interfaces import IAnnotations

from plone.z3cform.layout import FormWrapper
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from plone import api

from plone.app.discussion.interfaces import ICommentingTool, IConversation

from .. import _

class IComment(Interface):

    workflow_action = schema.Text(
        title=_(u"Workflow action"),
        required=True)

    comment = schema.Text(
        title=_(u"Comment"),
        description=_(u"You can enter a note."),
        required=False)


class WfCommentForm(form.AddForm):
    fields = Fields(IComment)
    fields['workflow_action'].mode = HIDDEN_MODE
    next_url = None

    def updateActions(self):
        super(WfCommentForm, self).updateActions()
        self.actions["save"].addClass("context")
        self.actions["cancel"].addClass("standalone")

    def updateWidgets(self):
        super(WfCommentForm, self).updateWidgets()
        if 'workflow_action' in self.request:
            self.widgets['workflow_action'].value = (
                self.request['workflow_action'])

    @button.buttonAndHandler(_(u'Refuse'), name='save')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._finishedAdd = True

        comment = data['comment'] or u""
        comment = comment.strip()

        if comment:
            portal_membership = getToolByName(self.context, 'portal_membership')
            # Member
            member = portal_membership.getAuthenticatedMember()
            username = member.getUserName()
            email = member.getProperty('email')
            fullname = member.getProperty('fullname')
            if not fullname or fullname == '':
                fullname = member.getUserName()
            # memberdata is stored as utf-8 encoded strings
            elif isinstance(fullname, str):
                fullname = unicode(fullname, 'utf-8')
            if email and isinstance(email, str):
                email = unicode(email, 'utf-8')

            # add comment to validation objects
            catalog = api.portal.get_tool('portal_catalog')
            container_path = '/'.join(aq_parent(self.context).getPhysicalPath())
            tasks = catalog.searchResults({'path': {'query': container_path},
                'portal_type': 'validation', 'review_state': 'todo'})

            for validation_object in tasks:
                annotations = IAnnotations(validation_object.getObject())
                if not 'related_version_id' in annotations:
                    continue
                if annotations['related_version_id'] != self.context.id:
                    continue

                comment_object = createObject('plone.Comment')
                comment_object.creator = username
                comment_object.author_username = username
                comment_object.author_name = fullname
                comment_object.author_email = email
                comment_object.creation_date = datetime.utcnow()
                comment_object.modification_date = datetime.utcnow()
                comment_object.text = comment

                conversation = IConversation(validation_object.getObject())
                conversation.addComment(comment_object)

        api.content.transition(obj=self.context, transition=data['workflow_action'])
        self.context.reindexObject(idxs=['review_state'])
        self.next_url = aq_parent(self.context).absolute_url()

    @button.buttonAndHandler(_(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedAdd = True
        self.next_url = aq_parent(self.context).absolute_url()

    def nextURL(self):
        return self.next_url


class WfCommentView(FormWrapper, BrowserView):
    form = WfCommentForm

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        FormWrapper.__init__(self, context, request)
