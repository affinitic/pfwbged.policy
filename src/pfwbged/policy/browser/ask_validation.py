from five import grok

from z3c.form import button
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import getUtility
from zope.i18n import translate

from Acquisition import aq_inner, aq_chain, aq_parent

from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.i18n import MessageFactory as DMF
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer, getAdditionalSchemata
from plone.supermodel import model

from Products.CMFPlone.utils import base_hasattr
from Products.statusmessages.interfaces import IStatusMessage

from collective.task.content.validation import IValidation

from pfwbged.policy import _


class IWorkflowAction(model.Schema):
    """Simple schema that contains workflow action hidden field"""
    workflow_action = schema.TextLine(title=_(u'Workflow action'),
                                      required=False
                                      )

class AskValidation(DefaultAddForm):
    """Ask validation custom add form
    """
    description = u""
    portal_type = 'validation'

    def updateWidgets(self):
        """Update widgets then add workflow_action value to workflow_action field"""
        version = self.context
        self.request.form["form.widgets.ITarget.target"] = ('/'.join(version.getPhysicalPath()),)
        if 'form.widgets.title' not in self.request.form:
             self.request.form["form.widgets.title"] = translate(_(u"Validation application for version ${version}",
                                                                 mapping={'version': version.Title()}), context=self.request)

        super(AskValidation, self).updateWidgets()
        if 'workflow_action' in self.request:
            self.widgets['workflow_action'].value = (
                self.request['workflow_action'])

    @property
    def additionalSchemata(self):
        additional = []
        behaviors = getAdditionalSchemata(portal_type=self.portal_type)
        for behavior in behaviors:
            if behavior.__name__ != 'IAllowDiscussion':
                additional.append(behavior)
        return additional

    def add(self, object):
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        container = aq_parent(aq_inner(self.context))
        new_object = addContentToContainer(container, object)
        # execute transition on version
        api.content.transition(self.context, transition='submit')

        if fti.immediate_view:
            self.immediate_view = "%s/%s/%s" % (container.absolute_url(), new_object.id, fti.immediate_view,)
        else:
            self.immediate_view = "%s/%s" % (container.absolute_url(), new_object.id)

    @property
    def label(self):
        return _(u"Ask validation")
