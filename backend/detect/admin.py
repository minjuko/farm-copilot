from django.contrib import admin

from .models import Pest, PestDetection, PestModelClass

admin.site.register(Pest)
admin.site.register(PestDetection)
admin.site.register(PestModelClass)
