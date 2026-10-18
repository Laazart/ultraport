from django.contrib import admin
from .models import Usuario, Rol, Contrato

admin.site.register(Usuario)
admin.site.register(Rol)
admin.site.register(Contrato)