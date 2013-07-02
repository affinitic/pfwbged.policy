from zope.component import getUtility
from zope.i18n import translate

from Acquisition import aq_inner, aq_parent

from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer, getAdditionalSchemata

from collective.task.content.opinion import IOpinion

from pfwbged.policy import _


class AskOpinion(DefaultAddForm):
    """Ask opinion custom add form
    """
    description = u""
    portal_type = 'opinion'

    def updateWidgets(self):
        """Update widgets then add workflow_action value to workflow_action field"""
        version = self.context
        self.request.form["form.widgets.ITarget.target"] = ('/'.join(version.getPhysicalPath()),)
        if 'form.widgets.title' not in self.request.form:
             self.request.form["form.widgets.title"] = translate(_(u"Opinion application for version ${version}",
                                                                 mapping={'version': version.Title()}),
                                                                 context=self.request)

        super(AskOpinion, self).updateWidgets()
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

        if fti.immediate_view:
            self.immediate_view = "%s/%s/%s" % (container.absolute_url(), new_object.id, fti.immediate_view,)
        else:
            self.immediate_view = "%s/%s" % (container.absolute_url(), new_object.id)

    @property
    def label(self):
        return _(u"Ask opinion")
