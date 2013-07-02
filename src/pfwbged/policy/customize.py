from plone.directives.form.value import default_value
from plone.directives.form.value import widget_label

from collective.dms.basecontent.dmsdocument import IDmsDocument

from . import _


@widget_label(field=IDmsDocument['treating_groups'])
def change_treating_groups_label(data):
    return _(u"Can edit")


@widget_label(field=IDmsDocument['recipient_groups'])
def change_recipent_groups_label(data):
    return _(u"Can view")