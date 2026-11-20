from django.conf import settings
from django.db import models
from django.utils import timezone

from .acciones import ACCIONES, ENTIDADES


class RegistroAuditoria(models.Model):
    """Quién hizo qué y cuándo. Se escribe solo con auditoria.services.registrar()."""
    id_registro = models.AutoField(primary_key=True)
    # Null = acción del sistema. Los usuarios no se borran (solo se desactivan).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_actor', related_name='registros_auditoria',
    )
    accion = models.CharField(max_length=50, choices=ACCIONES)
    entidad = models.CharField(max_length=30, choices=ENTIDADES)
    id_entidad = models.PositiveIntegerField(null=True, blank=True)
    # Breve y sin datos sensibles (ver CLAVES_PROHIBIDAS en services.py).
    detalle = models.JSONField(default=dict, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'registro_auditoria'
        ordering = ['-fecha', '-id_registro']
        indexes = [
            models.Index(fields=['-fecha'], name='auditoria_fecha_idx'),
            models.Index(fields=['actor', '-fecha'], name='auditoria_actor_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.fecha:%Y-%m-%d %H:%M} {self.accion} {self.entidad}#{self.id_entidad}'
