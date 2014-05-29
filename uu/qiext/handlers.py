from zope.component.hooks import getSite
from plone.dexterity.utils import createContentInContainer

from uu.qiext.user.handlers import handle_workspace_added


FIXTURE_SPEC = (
    ('uu.eventintegration.calendar', u'Calendar'),
    ('uu.formlibrary.library', u'Form library'),
    ('uu.formlibrary.measurelibrary', u'Measures'),
    )


def project_addfixtures(context):
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
        project_addfixtures(context)

