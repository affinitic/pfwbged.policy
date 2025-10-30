# -*- coding: utf-8 -*-
import logging
import transaction

from Acquisition import aq_base
from Acquisition import aq_inner
from Products.CMFPlone.utils import getToolByName
from plone import api
from plone.z3cform.layout import FormWrapper
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import schema
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.component.hooks import setSite
from zope.globalrequest import getRequest
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import directlyProvides
from zope.interface import implements
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from pfwbged.policy import _


class Counter:
    def __init__(self):
        self.modified = 0
        self.ignored = 0
        self.last_commit_at = 0

    @property
    def time_to_commit(self):
        if self.modified > 0 and self.modified % 1000 == 0 and self.modified > self.last_commit_at:
            self.last_commit_at = self.modified
            return True
        else:
            return False


def reindex(site):
    """re-compute indexes containing principals or security (allowedRolesAndUsers)"""

    indexes = [
        "Creator",
        "responsible",
        "enquirer",
        "allowedRolesAndUsers",
        # "commentators",
    ]

    # source: Products.ZCatalog.ZCatalog.ZCatalog.reindexIndex
    portal_catalog = getToolByName(site, "portal_catalog")
    request = getRequest()
    log = logging.getLogger('Zope.ZCatalog')
    log.warning("reindexing ...")
    paths = portal_catalog._catalog.uids.keys()

    for p in paths:
        obj = portal_catalog.resolve_path(p)
        if obj is None:
            obj = portal_catalog.resolve_url(p, request)
        if obj is None:
            log.error('reindexIndex could not resolve '
                      'an object from the uid %r.' % p)
        else:
            portal_catalog.catalog_object(
                obj,
                p,
                idxs=indexes,
                update_metadata=1,
                pghandler=None
            )

    transaction.commit()


def group_ids_vocabulary(context):
    portal_groups = api.portal.get_tool(name='portal_groups')
    ids = portal_groups.getGroupIds()
    terms = [SimpleTerm(value=gid, token=gid, title=gid) for gid in sorted(ids)]
    return SimpleVocabulary(terms)

directlyProvides(group_ids_vocabulary, IContextSourceBinder)


class IRenameGroupForm(Interface):

    groups_to_rename = schema.List(
        title=_('label_groups_to_rename', default=u'Groups to rename'),
        description=_(
            'help_groups_to_rename',
            default=u'Select the groups you want to rename.'
        ),
        value_type=schema.Choice(
            source=group_ids_vocabulary,
        ),
        required=True,
    )

    new_names = schema.Text(
        title=_('label_new_names', default=u'New names'),
        description=_(
            'help_new_names',
            default=(
                u'Enter the new name for each selected group, one per line, '
                u'in the same order as the groups above.'
            )
        ),
        required=True,
    )


class RenameGroupForm(form.Form):
    fields = field.Fields(IRenameGroupForm)
    label = _(u"Rename Plone groups")
    description = _(u"This action can take more than an hour. Please use it during off-peak hours.")
    ignoreContext = True

    @button.buttonAndHandler(_(u"Launch renaming"))
    def handle_rename(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        portal_groups = api.portal.get_tool(name='portal_groups')
        existing_ids = portal_groups.getGroupIds()

        groups_to_rename = data.get("groups_to_rename")
        new_names = [
            x.strip().decode("utf8") for x in data.get("new_names").split("\r\n") if x.strip()
        ]

        overwrites = set(new_names).intersection(existing_ids)
        if overwrites:
            raise Invalid(
                _(
                    u"The following group(s) already exist: ${groups}",
                    mapping={"groups": ", ".join(overwrites)},
                )
            )

        if len(groups_to_rename) != len(new_names):
            raise Invalid(
                _(
                    u"The number of groups to rename does not match the number of new names.",
                )
            )

        if len(set(new_names)) < len(new_names):
            raise Invalid(
                _(
                    u"Some of new names are used multiple times.",
                )
            )

        mapping_names = dict(zip(groups_to_rename, new_names))
        self._rename_groups(mapping_names)

        self.status = _(u"The groups have been renamed.")

    def _rename_groups(self, mapping_names):

        portal = api.portal.get()
        counter = Counter()

        # create new plone groups
        for old_id, new_id in mapping_names.items():
            group_roles = api.group.get_roles(groupname=old_id)
            api.group.create(new_id, title=new_id, roles=group_roles)

        # object migration over all the site
        def migrate_object(portal_setup, obj_path):
            obj = api.content.get(path=obj_path)
            dirty_obj = False

            # enumerable fields
            for field_name, field_type in (
                    ("treating_groups", list),
                    ("recipient_groups", list),
                    ("treated_by", list),
                    ("in_copy", list),
                    ("responsible", tuple),
                    ("enquirer", tuple),
                    ("creators", tuple),
                    # ("commentators", ),
            ):
                if hasattr(obj, field_name):
                    new_field_value = []
                    dirty_field = False
                    original_field_value = getattr(obj, field_name)
                    if not original_field_value:
                        continue
                    for principal_id in original_field_value:
                        if principal_id in mapping_names:
                            new_field_value.append(mapping_names[principal_id])
                            dirty_field = True
                            dirty_obj = True
                        else:
                            new_field_value.append(principal_id)
                    if dirty_field:
                        if field_type is tuple:
                            new_field_value = tuple(new_field_value)
                        setattr(obj, field_name, new_field_value)

            # choice fields
            for field_name in (
                    "original_paper_version",
            ):
                if hasattr(obj, field_name):
                    original_field_value = getattr(obj, field_name)
                    if original_field_value in mapping_names:
                        setattr(obj, field_name, mapping_names[original_field_value])
                        dirty_obj = True

            # - workflow history

            if hasattr(aq_base(obj), 'workflow_history'):
                history = obj.workflow_history
                if history:
                    for workflow_id in history.keys():
                        dirty_actions = False
                        actions = list(history[workflow_id])
                        for action in actions:
                            old_actor = action.get("actor")
                            if old_actor in mapping_names:
                                action["actor"] = mapping_names[old_actor]
                                dirty_actions = True
                                dirty_obj = True
                        if dirty_actions:
                            obj.workflow_history[workflow_id] = tuple(actions)

            pfwbged_history = None
            try:
                annotations = IAnnotations(aq_inner(obj))
                pfwbged_history = annotations.get("pfwbged_history")
            except TypeError:
                pass
            if pfwbged_history:
                for action in pfwbged_history:

                    old_actor = action.get("actor_name")
                    if old_actor in mapping_names:
                        action["actor_name"] = mapping_names[old_actor]
                        dirty_obj = True

                    old_value = action.get("value")
                    if type(old_value) == list:
                        new_value = []
                        for value_element in old_value:
                            if value_element in mapping_names:
                                new_value.append(mapping_names[value_element])
                            else:
                                new_value.append(value_element)
                        if new_value != old_value:
                            action["value"] = new_value
                            dirty_obj = True

            # - update local roles

            if hasattr(obj, "get_local_roles"):
                for principal_id, roles in obj.get_local_roles():
                    if principal_id in mapping_names:
                        obj.manage_delLocalRoles([principal_id])  # TODO: nécessaire ?
                        obj.manage_setLocalRoles(mapping_names[principal_id], roles)
                        dirty_obj = True

            if dirty_obj:
                obj._p_changed = True
                counter.modified += 1
            else:
                counter.ignored += 1

            if counter.time_to_commit:
                transaction.commit()
                print("... modified objects:", counter.modified)

        portal.ZopeFindAndApply(
            portal,
            search_sub=True,
            apply_func=migrate_object,
        )

        # delete old plone groups
        for old_id in mapping_names.keys():
            api.group.delete(groupname=old_id)

        transaction.commit()

        # reindex site
        reindex(portal)


class RenameGroupView(FormWrapper):
    form = RenameGroupForm
