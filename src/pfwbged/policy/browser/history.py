from plone import api
from plone.app.layout.viewlets.content import ContentHistoryView as BaseHistoryView

from .. import _
from ..menu import dmsfile_wfactions_mapping, IGNORE_

class ContentHistoryView(BaseHistoryView):

    def _modify_title(self, actions):
        for action in actions:
            version = self.context.Title()
            title = dmsfile_wfactions_mapping.get(action['action'],
                    _(u"Create version ${version}"))
            title = IGNORE_(title, mapping={'version': version})
            action['transition_title'] = title

    def workflowHistory(self, complete=True):
        review_history = []
        results = super(ContentHistoryView, self).workflowHistory(complete)
        review_history.extend(results)

        catalog = api.portal.get_tool('portal_catalog')
        folder_path = '/'.join(self.context.getPhysicalPath())
        query = {'path': {'query' : folder_path},
                 'portal_type': 'dmsmainfile'}
        brains = catalog.unrestrictedSearchResults(query)
        old_context = self.context
        for brain in brains:
            version = brain.getObject()
            self.context = version
            results = super(ContentHistoryView, self).workflowHistory(complete)
            self._modify_title(results)
            review_history.extend(results)

        self.context = old_context
        return review_history
