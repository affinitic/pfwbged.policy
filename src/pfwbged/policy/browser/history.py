from plone import api
from plone.app.layout.viewlets.content import ContentHistoryView as BaseHistoryView

from AccessControl import Unauthorized

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

        # insert workflow history for all versions
        query = {'path': {'query' : folder_path},
                 'portal_type': 'dmsmainfile'}
        brains = catalog.unrestrictedSearchResults(query)
        old_context = self.context
        for brain in brains:
            try:
                version = brain.getObject()
            except Unauthorized:
                continue
            self.context = version
            results = super(ContentHistoryView, self).workflowHistory(complete)
            self._modify_title(results)
            review_history.extend(results)
        self.context = old_context

        # append history entries for the various tasks
        query = {'path': {'query' : folder_path},
                 'portal_type': ['information', 'opinion', 'task', 'validation']}
        brains = catalog.unrestrictedSearchResults(query)
        for brain in brains:
            try:
                task = brain.getObject()
            except Unauthorized:
                continue
            review_history.append({
                'actor': None,
                'actorid': task.creators[0],
                'actor_home': '',
                'action': task.portal_type,
                'time': task.creation_date,
                'transition_title': task.title,
                'type': None})

        # makes sure the history is kept sorted
        review_history.sort(lambda x, y: cmp(x.get('time'), y.get('time')))

        return review_history
