from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.container.interfaces import INameChooser

from Products.Five.browser import BrowserView


class ImportGroupFolders(BrowserView):
    def __call__(self):
        portal = self.context
        factory = getUtility(IVocabularyFactory, 'plone.principalsource.Groups')
        vocabulary = factory(self.context)
        chooser = INameChooser(self.context)
        for term in vocabulary:
            if term.value in ('Administrators', 'Reviewers',
                    'Site Administrators', 'AuthenticatedUsers'):
                # ignore system groups
                continue
            if term.title.startswith('(Group) '):
                term.value = chooser.chooseName(term.value, self.context)
                term.title = term.title[len('(Group) '):] # remove '(Group) '
            if term.value in portal['dossiers']:
                continue
            folder = portal['dossiers'].invokeFactory('pfwbgedfolder',
                    term.value, title=term.title,
                    treating_groups=[term.value],
                    recipient_groups=[term.value])
        return 'OK'
