from plone.app.dexterity.behaviors.discussion import IAllowDiscussion
from plone.directives.form.value import default_value
from plone.directives.form.value import widget_label

from collective.dms.basecontent.dmsdocument import IDmsDocument

from . import _


@default_value(field=IAllowDiscussion['allow_discussion'])
def allow_discussion_default_value(data):
    return True


@widget_label(field=IDmsDocument['treating_groups'])
def change_treating_groups_label(data):
    return _(u"Can edit")


@widget_label(field=IDmsDocument['recipient_groups'])
def change_recipent_groups_label(data):
    return _(u"Can view")