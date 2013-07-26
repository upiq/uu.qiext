from plone.app.users.browser.personalpreferences import UserDataConfiglet
from plone.app.users.browser.personalpreferences import PersonalPreferencesConfiglet

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


from uu.qiext.user.interfaces import IWorkspaceRoster


class WorkspaceUserInfoForm(UserDataConfiglet):

    template = ViewPageTemplateFile('userprops.pt')
    
    def __init__(self, context, request):
        super(WorkspaceUserInfoForm, self).__init__(context, request)
        if self.userid is not None:
            roster = IWorkspaceRoster(context)
            if self.userid not in roster:
                self.userid = None

