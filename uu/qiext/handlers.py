from zope.component.hooks import getSite
from plone.dexterity.utils import createContentInContainer

from uu.qiext.user.handlers import handle_workspace_added
from uu.qiext.user.interfaces import ISiteMembers, IWorkspaceRoster

FIXTURE_SPEC = (
    ('uu.eventintegration.calendar', u'Calendar'),
    ('uu.formlibrary.library', u'Form library'),
    ('uu.formlibrary.measurelibrary', u'Measures'),
    )


def fix_current_user(context):
    """
    When a project is added, the current user context may not yet
    have Manager role added to the generated user object, even if the
    user is technically a member of the group.  This is only an issue
    when we attempt to do something requiring a group membership added
    in the same transation.  This is a workaround.
    """
    current = ISiteMembers(getSite()).current()
    roster = IWorkspaceRoster(context)
    manager_group = roster.groups.get('managers').pas_group()[0]
    current._addGroups((manager_group,))


def project_add_fixtures(context):
    fix_current_user(context)
    wftool = getSite().portal_workflow
    for ftiname, title in FIXTURE_SPEC:
        fixture = createContentInContainer(
            container=context,
            portal_type=ftiname,
            title=title,
            )
        wftool.doActionFor(fixture, 'restrict')
        if fixture.objectIds():
            for content in fixture.objectValues():
                wftool.doActionFor(content, 'restrict')
        fixture.reindexObject()


def project_afteradd(context, event):
    add_fixtures = len(context.objectIds()) == 0  # empty, not copy
    if add_fixtures:
        # call handle_workspace_added because order matters for
        # permissions; side-effect is that this may be called twice:
        handle_workspace_added(context, event)
        project_add_fixtures(context)

