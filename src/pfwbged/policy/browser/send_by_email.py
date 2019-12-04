# -*- encoding: utf-8 -*-

import random
import logging
from datetime import datetime
from DateTime import DateTime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from collective.dms.basecontent.widget import AjaxChosenMultiFieldWidget
from zope.interface import Interface
from zope import schema
from zope.component import createObject, queryUtility
from z3c.form import form, button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE
from zope.annotation.interfaces import IAnnotations

from Acquisition import aq_inner, aq_parent

from plone.z3cform.layout import FormWrapper
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from plone import api

from .. import _


class IMail(Interface):
    recipients = schema.List(
        title=_(u"Recipients"),
        description=_(u"Email addresses of the recipients"),
        required=True,
        value_type=schema.Choice(
            vocabulary=u'collective.dms.basecontent.ldap_emails',
        ),
    )

    subject = schema.TextLine(title=_(u"Subject"), required=True)
    comment = schema.Text(
        title=_(u"Comment"),
        description=_(u"You can enter a note."),
        required=False)


class MailForm(form.AddForm):
    fields = Fields(IMail)
    fields['recipients'].widgetFactory = AjaxChosenMultiFieldWidget
    next_url = None

    def updateActions(self):
        super(MailForm, self).updateActions()
        self.actions["save"].addClass("context")
        self.actions["cancel"].addClass("standalone")

    def updateWidgets(self):
        super(MailForm, self).updateWidgets()

    @button.buttonAndHandler(_(u'Send'), name='save')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._finishedAdd = True

        subject = data['subject']
        recipients = data['recipients']
        comment = data.get('comment')

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['To'] = ', '.join(recipients)

        ldap_email = api.user.get_current().getProperty('email')
        if not isinstance(ldap_email, str):
            ldap_email = None

        msg['From'] = api.user.get_current().getProperty('email', None) or \
                api.user.get_current().email or \
                api.portal.get().getProperty('email_from_address') or \
                'admin@localhost'

        if comment:
            msg.attach(MIMEText(comment, _charset='utf-8'))

        ctype = self.context.file.contentType or 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(self.context.file.data)
        encoders.encode_base64(attachment)
        if self.context.file.filename:
            attachment.add_header('Content-Disposition', 'attachment',
                    filename=self.context.file.filename)

        msg.attach(attachment)

        try:
            self.context.MailHost.send(msg.as_string())
        except Exception as e:
            # do not abort transaction in case of email error
            log = logging.getLogger('pfwbged.policy')
            log.exception(e)
            self.context.plone_utils.addPortalMessage(_('Error sending email'))
        else:
            document = aq_parent(self.context)
            annotations = IAnnotations(document)
            if not 'pfwbged_history' in annotations:
                annotations['pfwbged_history'] = []
            annotations['pfwbged_history'].append({'time': DateTime(),
                'action_id': 'pfwbged_mail',
                'action': 'Sent by email',
                'actor_name': api.user.get_current().getId(),
                'to': msg['To'],
                'version': self.context.Title(),
                })
            # assign it back as a change to the list won't trigger the
            # annotation to be saved on disk.
            annotations['pfwbged_history'] = annotations['pfwbged_history'][:]

        self.next_url = aq_parent(self.context).absolute_url()

    @button.buttonAndHandler(_(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedAdd = True
        self.next_url = aq_parent(self.context).absolute_url()

    def nextURL(self):
        return self.next_url


class SendMailView(FormWrapper, BrowserView):
    form = MailForm

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        FormWrapper.__init__(self, context, request)
