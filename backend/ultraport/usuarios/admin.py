from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import Usuario, Rol, Contrato, Puesto, TipoLicencia, Maquinaria, UsuarioPuesto, UsuarioLicencia, UsuarioMaquinaria


class UsuarioCreacionAdminForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ('correo', 'rut', 'nombres', 'apellidos', 'telefono', 'id_rol', 'id_contrato')


class UsuarioCambioAdminForm(UserChangeForm):
    """La contraseña se muestra como hash de solo lectura (no editable como texto)."""

    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = '__all__'
        field_classes = {}


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Admin de Usuario basado en UserAdmin: la contraseña solo se cambia con el
    formulario de Django (enlace "cambiar contraseña"), que aplica
    AUTH_PASSWORD_VALIDATORS (incluido el historial) y guarda con set_password.
    """
    form = UsuarioCambioAdminForm
    add_form = UsuarioCreacionAdminForm

    fieldsets = (
        (None, {'fields': ('correo', 'password')}),
        ('Datos personales', {'fields': ('rut', 'nombres', 'apellidos', 'telefono')}),
        ('Rol y contrato', {'fields': ('id_rol', 'id_contrato', 'estado')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'fecha_creacion')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('correo', 'rut', 'nombres', 'apellidos', 'telefono', 'id_rol', 'id_contrato',
                       'password1', 'password2'),
        }),
    )
    readonly_fields = ('last_login', 'fecha_creacion')
    list_display = ('correo', 'rut', 'nombres', 'apellidos', 'id_rol', 'estado', 'is_staff')
    list_filter = ('id_rol', 'estado', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('correo', 'rut', 'nombres', 'apellidos')
    ordering = ('apellidos', 'nombres')


admin.site.register(Rol)
admin.site.register(Contrato)
admin.site.register(Puesto)
admin.site.register(TipoLicencia)
admin.site.register(Maquinaria)
admin.site.register(UsuarioPuesto)
admin.site.register(UsuarioLicencia)
admin.site.register(UsuarioMaquinaria)
