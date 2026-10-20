from django.contrib import admin
from .models import Usuario, Rol, Contrato, Puesto, TipoLicencia, Maquinaria, UsuarioPuesto, UsuarioLicencia, UsuarioMaquinaria

admin.site.register(Usuario)
admin.site.register(Rol)
admin.site.register(Contrato)
admin.site.register(Puesto)
admin.site.register(TipoLicencia)
admin.site.register(Maquinaria)
admin.site.register(UsuarioPuesto)
admin.site.register(UsuarioLicencia)
admin.site.register(UsuarioMaquinaria)