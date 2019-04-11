from zope.i18n import translate

from copy import deepcopy
from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.utils import addContentToContainer, getAdditionalSchemata
from z3c.form.interfaces import HIDDEN_MODE

from zope.annotation.interfaces import IAnnotations
import zope.event
import zope.lifecycleevent

from z3c.form import button
from pfwbged.policy import _


class AskValidations(DefaultAddForm):
    """Ask validation custom add form
    """
    description = u""
    portal_type = 'validation'

    @property
    def label(self):
        return u"Demander des validations"

    @property
    def action(self):
        return self.request.getURL() + '?documents=' + self.request.documents

    @property
    def additionalSchemata(self):
        additional = []
        behaviors = getAdditionalSchemata(portal_type=self.portal_type)
        for behavior in behaviors:
            if behavior.__name__ != 'IAllowDiscussion':
                additional.append(behavior)
        return additional

    def updateFields(self):
        super(AskValidations, self).updateFields()
        self.fields['title'].mode = HIDDEN_MODE

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        for document_id in self.request.documents.split(','):
            base_document = api.content.get(str(document_id))
            self.ask_validation(base_document, data)

        self._finishedAdd = True
        return

    def ask_validation(self, base_document, data):
        for child in reversed(base_document.values()):
            if child.portal_type == 'dmsmainfile':
                last_version = child
                break

        _data = deepcopy(data)
        _data['title'] = translate(
            _(u"Validation application for version ${version}",
              mapping={'version': last_version.Title()}),
            context=self.request)
        _data['ITarget.target'] = last_version

        new_validation = self.create(_data)
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(new_validation))
        addContentToContainer(base_document, new_validation)

        # annotate the validation task with the related version, it can later
        # be used to match the task against the correct version.
        annotations = IAnnotations(new_validation)
        annotations['related_version_id'] = last_version.id

        # execute transition on version
        api.content.transition(last_version, transition='submit')
        last_version.reindexObject(idxs=['review_state'])
