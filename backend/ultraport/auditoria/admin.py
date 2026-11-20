from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Solo lectura: el registro no se crea, edita ni borra a mano."""
    list_display = ('fecha', 'actor', 'accion', 'entidad', 'id_entidad')
    list_filter = ('accion', 'entidad')
    search_fields = ('actor__correo', 'actor__nombres', 'actor__apellidos')
    date_hierarchy = 'fecha'
    list_select_related = ('actor',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
