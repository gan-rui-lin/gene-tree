from django.contrib import admin

from .models import Genealogy, GenealogyUser, Marriage, Member, ParentChild, User

admin.site.register(User)
admin.site.register(Genealogy)
admin.site.register(GenealogyUser)
admin.site.register(Member)
admin.site.register(ParentChild)
admin.site.register(Marriage)
