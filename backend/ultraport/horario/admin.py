from django.contrib import admin
from .models import NotificacionInasistencia


@admin.register(NotificacionInasistencia)
class NotificacionInasistenciaAdmin(admin.ModelAdmin):
    list_display = ('id_notificacion', 'id_usuario', 'fecha_inicio', 'fecha_fin', 'estado', 'fecha_registro')
    list_filter = ('estado',)
