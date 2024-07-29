"""
author : mohan
app_name : form_generator
"""
from django.contrib import admin
from .models import *

admin.site.register(FormDataInfo)
admin.site.register(FilledFormData)
admin.site.register(UserData)
admin.site.register(CreateProcess)
admin.site.register(Case)
admin.site.register(Rule)
admin.site.register(Sla)
admin.site.register(FormPermission)

