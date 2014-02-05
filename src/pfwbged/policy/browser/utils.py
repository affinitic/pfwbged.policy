from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

from Products.Five.browser import BrowserView


class ImportGroupFolders(BrowserView):
    def __call__(self):
        portal = self.context
        factory = getUtility(IVocabularyFactory, 'plone.principalsource.Groups')
        vocabulary = factory(self.context)
        for term in vocabulary:
            if term.value in ('Administrators', 'Reviewers',
                    'Site Administrators', 'AuthenticatedUsers'):
                # ignore system groups
                continue
            if term.value in portal['dossiers']:
                continue
            folder = portal['dossiers'].invokeFactory('pfwbgedfolder',
                    term.value, title=term.title,
                    treating_groups=[term.value])
        return 'OK'
