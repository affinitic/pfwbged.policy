from five import grok

from zope.i18n import translate
from zope.i18nmessageid import MessageFactory

from plone import api
from plone.app.layout.viewlets.interfaces import IAboveContentBody

from Products.CMFCore.interfaces._content import IContentish
from Products.CMFCore.WorkflowCore import WorkflowException
from plone.app.layout.globals.interfaces import IViewView

from pfwbged.policy.interfaces import IPfwbgedPolicyLayer

PMF = MessageFactory('plone')

grok.context(IContentish)


class ReviewStateViewlet(grok.Viewlet):

    grok.name('review_state')
    grok.viewletmanager(IAboveContentBody)
    grok.view(IViewView)
    grok.layer(IPfwbgedPolicyLayer)

    def render(self):
        try:
            state = api.content.get_state(self.context)
            portal_type = self.context.portal_type
            wtool = api.portal.get_tool('portal_workflow')
            state_title = wtool.getTitleForStateOnType(state, portal_type)
            state_title = translate(PMF(state_title), context=self.request)
        except WorkflowException:
            return u""
        data = {}
        data['label'] = translate(PMF(u"State"), context=self.request)
        data['review_state'] = state_title
        return """<div id="formfield-form-widgets-review_state" class="field z3cformInlineValidation kssattr-fieldname-review_state" data-fieldname="review_state">
    <label class="horizontal" for="form-widgets-review_state">%(label)s</label>
    <div class="fieldErrorBox"></div>
    <span id="form-widgets-review_state" class="review_state-field" style="width:280px;">%(review_state)s</span>
</div>""" % data
