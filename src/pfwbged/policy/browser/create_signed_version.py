from copy import deepcopy

from five import grok

from zope.annotation.interfaces import IAnnotations

from plone import api

from collective.dms.basecontent.dmsfile import IDmsFile


class CreateSignedVersion(grok.View):
    """Create signed version"""

    grok.name('create_signed_version')
    grok.context(IDmsFile)
    grok.require("zope2.View")

    def render(self):
        copied_version = self.context
        container = copied_version.getParentNode()
        annotations = IAnnotations(container)
        if 'higher_version' not in annotations:
            version_number = 1
        else:
            version_number = annotations['higher_version'].value
        # create a new version
        new_version_id = container.invokeFactory("dmsmainfile", version_number,
                                                 title=str(version_number))
        new_version = container[new_version_id]
        new_version.signed = True
        api.content.transition(new_version, "finish_without_validation")
        local_roles = copied_version.__ac_local_roles__
        new_version.__ac_local_roles__ = deepcopy(local_roles)
        new_version.reindexObject()
        # copy local roles
        self.request.response.redirect(new_version.absolute_url() + "/edit")
        return ""
