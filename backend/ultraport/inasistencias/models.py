from django.conf import settings
from django.db import models


class NotificacionInasistencia(models.Model):
    PENDIENTE = 'pendiente'
    APROBADO = 'aprobado'
    RECHAZADO = 'rechazado'
    ESTADOS = [
        (PENDIENTE, 'Pendiente'),
        (APROBADO, 'Aprobado'),
        (RECHAZADO, 'Rechazado'),
    ]

    id_notificacion = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='id_usuario',
        related_name='notificaciones_inasistencia',
    )
    # TODO: CONVERTIR TURNO EN FOREIGNKEY, db_column='id_turno' cuando lo creemos!!!!!!
    id_turno = models.IntegerField(null=True, blank=True, db_column='id_turno')
    motivo = models.CharField(max_length=255)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    # se guarda la ruta del archivo (varchar 255) la url completa la arma el serializer.
    url_adjunto = models.FileField(
        upload_to='inasistencias/%Y/%m/', max_length=255, null=True, blank=True,
        db_column='url_adjunto',
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificacion_inasistencia'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'#{self.id_notificacion} {self.id_usuario} ({self.estado})'
