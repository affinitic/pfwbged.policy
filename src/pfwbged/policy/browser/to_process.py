# -*- encoding: utf-8 -*-

from zope.interface import Interface
from zope import schema
from z3c.form import form, button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE

from plone.z3cform.layout import FormWrapper
from Products.Five.browser import BrowserView
from plone import api


from ..subscribers.mail import incoming_mail_attributed
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

    @button.buttonAndHandler(_(u'Save'), name='save')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._finishedAdd = True

        comment = data['comment'] or u""
        comment = comment.strip()

        incomingmail = self.context
        api.content.transition(obj=incomingmail, transition=data['workflow_action'])
        incomingmail.reindexObject(idxs=['review_state'])
        incoming_mail_attributed(incomingmail, comment)
        self.next_url = self.context.absolute_url()

    @button.buttonAndHandler(_(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedAdd = True
        self.next_url = self.context.absolute_url()

    def nextURL(self):
        return self.next_url


class WfCommentView(FormWrapper, BrowserView):
    form = WfCommentForm

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        FormWrapper.__init__(self, context, request)


class WfProcessNoCommentView(BrowserView):
    def __call__(self):
        incomingmail = self.context
        api.content.transition(obj=incomingmail, transition='to_process')
        incomingmail.reindexObject(idxs=['review_state'])
        incoming_mail_attributed(incomingmail, u'')
        self.request.response.redirect(self.context.absolute_url())
