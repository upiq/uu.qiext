from zope.component.hooks import getSite
from plone.dexterity.utils import createContentInContainer


FIXTURE_SPEC = (
    ('uu.eventintegration.calendar', u'Calendar'),
    ('uu.formlibrary.library', u'Form library'),
    ('uu.formlibrary.measurelibrary', u'Measures'),
    )


def project_afteradd(context, event):
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

