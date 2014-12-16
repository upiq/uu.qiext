from zope.i18nmessageid import MessageFactory

_ = MessageFactory('uu.qiext')

rename_dict = {
    'Products.qi.extranet.types.project Project':
        'collective.teamwork.content Project',
    'Products.qi.extranet.types.team Team':
        'collective.teamwork.content Workspace',
    'Products.qi.extranet.types.subteam SubTeam':
        'collective.teamwork.content Workspace',
}
