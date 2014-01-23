# event handlers for lifecycle events on projects and workspaces

from plone.app.layout.navigation.interfaces import INavigationRoot
from zope.component.hooks import getSite
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from Acquisition import aq_base

from uu.qiext.user.interfaces import ISiteMembers
from uu.qiext.user.workgroups import WorkspaceRoster
from uu.qiext.user.utils import sync_group_roles
from uu.qiext.utils import get_workspaces


_str = lambda v: v.encode('utf-8') if isinstance(v, unicode) else str(v)
_u = lambda v: v.decode('utf-8') if isinstance(v, str) else unicode(v)


def handle_workspace_copy(context, event):
    """
    On IObjectCopiedEvent, we do not have an acqusition-wrapped object
    yet, so we just need to flag the copy so that a handler for
    IObjectAddedEvent can be smart about the difference between a
    copy and a non-copy created workspace object.
    """
    # flag and original object for use/clear by subsequent handlers
    context._v_workspace_copy_of = event.original.getPhysicalPath()


def create_workspace_groups_roles(context):
    site = getSite()
    members = ISiteMembers(site)
    pasgroups = members.groups
    roster = WorkspaceRoster(context)
    for group in roster.groups.values():
        groupname, title = group.pas_group()
        if groupname not in pasgroups:
            print 'added ', groupname
            pasgroups.add(groupname, title=title)
        else:
            # update title of previously existing group (edge case)
            pasgroups.get(groupname).title = _u(title)
        # bind local roles, mapping group to roles from config
        sync_group_roles(context, groupname)
    if INavigationRoot.providedBy(context):
        # for newly added top-level (nav root workspaces or
        # projects), add owner/creator as a manager.
        authuser = members.current()
        if authuser is not None:
            authuser = authuser.getUserName()
            if authuser in members:
                roster.add(authuser)
                roster.groups['managers'].add(authuser)


def handle_workspace_pasted(context, event, original_path):
    """handle IObjectAddedEvent after a copy/paste opertion"""
    create_workspace_groups_roles(context)
    for workspace in get_workspaces(context):
        create_workspace_groups_roles(workspace)


def handle_workspace_added(context, event):
    """
    May be added via construction (new item) or copy (cloned item).
    Handle either case, creating new groups if needed.

    If context._v_workspace_copy is set attrbute, then consider the
    added itam a copy, not new, and act accordingly, then finally
    unset that attribute.
    """
    ob = aq_base(context)
    if hasattr(ob, '_v_workspace_copy_of'):
        original_path = getattr(ob, '_v_workspace_copy_of')
        handle_workspace_pasted(context, event, original_path)
        delattr(ob, '_v_workspace_copy_of')
        return
    create_workspace_groups_roles(context)


def handle_workspace_move_or_rename(context, event):
    if IObjectRemovedEvent.providedBy(event):
        return  # not a move with new/old, but a removal -- handled elsewhere
    if IObjectAddedEvent.providedBy(event):
        return  # not an add, but a move of existing
    site = getSite()
    pasgroups = ISiteMembers(site).groups
    roster = WorkspaceRoster(context)
    for workgroup in roster.groups.values():
        groupname, title = workgroup.pas_group()
        if groupname not in pasgroups:
            pasgroups.add(groupname, title=title)
        else:
            pasgroups.get(groupname).title = _u(title)


def handle_workspace_removal(context, event):
    """Handler for IObjectRemovedEvent on a workspace"""
    site = getSite()
    if site is None:
        return  # in case of recursive plone site removal, ignore
    pasgroups = ISiteMembers(site).groups
    roster = WorkspaceRoster(context)
    for group in roster.groups.values():
        groupname = group.pas_group()[0]
        if groupname in pasgroups:
            pasgroups.remove(groupname)
    # remove group names for nested workspaces (also, by implication,
    #   removed from the PAS group manager plugin).
    for workspace in get_workspaces(context):
        handle_workspace_removal(workspace, event=event)

