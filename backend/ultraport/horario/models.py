from django.conf import settings
from django.db import models
from datetime import date, datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from usuarios.models import Usuario, Puesto, TipoLicencia, Maquinaria


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
    id_turno = models.IntegerField(null=True, blank=True, db_column='id_turno')
    motivo = models.CharField(max_length=255)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    url_adjunto = models.FileField(
        upload_to='horario/inasistencias/%Y/%m/', max_length=255, null=True, blank=True,
        db_column='url_adjunto',
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificacion_inasistencia'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'#{self.id_notificacion} {self.id_usuario} ({self.estado})'
ESTADOS_ACTIVOS = ['borrador', 'confirmado']


class BloqueTurno(models.Model):
    id_bloque = models.AutoField(primary_key=True)
    nombre_bloque = models.CharField(max_length=20, unique=True)
    hora_inicio = models.TimeField()
    hora_termino = models.TimeField()
    orden_secuencia = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        db_table = 'bloque_turno'
        ordering = ['orden_secuencia']

    def __str__(self):
        return self.nombre_bloque

    @property
    def es_nocturno(self):
        return self.hora_termino <= self.hora_inicio

    def intervalo(self, fecha):
        """Devuelve (inicio, fin) como datetimes para la fecha dada."""
        inicio = datetime.combine(fecha, self.hora_inicio)
        fecha_fin = fecha + timedelta(days=1) if self.es_nocturno else fecha
        return inicio, datetime.combine(fecha_fin, self.hora_termino)

    def duracion_horas(self):
        inicio, fin = self.intervalo(date(2000, 1, 1))
        return (fin - inicio).total_seconds() / 3600


class Malla(models.Model):
    class Estados(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        PUBLICADA = 'publicada', 'Publicada'

    id_malla = models.AutoField(primary_key=True)
    fecha = models.DateField(unique=True)
    estado = models.CharField(max_length=20, choices=Estados.choices, default=Estados.BORRADOR)
    creado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='mallas_creadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'malla'
        ordering = ['-fecha']

    def __str__(self):
        return f'Malla {self.fecha}'

class Area(models.Model):
    id_area = models.AutoField(primary_key=True)
    nombre_area = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'area'
        ordering = ['nombre_area']

    def __str__(self):
        return self.nombre_area
class Turno(models.Model):
    id_turno = models.AutoField(primary_key=True)
    id_malla = models.ForeignKey(Malla, on_delete=models.CASCADE, related_name='turnos')
    id_area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='turnos', null=True, blank=True)    
    id_bloque = models.ForeignKey(BloqueTurno, on_delete=models.PROTECT)
    id_puesto = models.ForeignKey(Puesto, on_delete=models.PROTECT)
    id_maquinaria_req = models.ForeignKey(
        Maquinaria, on_delete=models.SET_NULL, null=True, blank=True
    )
    id_tipo_licencia_req = models.ForeignKey(
        TipoLicencia, on_delete=models.SET_NULL, null=True, blank=True
    )
    cupos = models.PositiveSmallIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'turno'
        ordering = ['id_area__nombre_area', 'id_bloque__orden_secuencia', 'id_puesto_id']

def __str__(self):
        return f'{self.id_malla.fecha} - {self.id_bloque} - {self.id_puesto}'
class Asignacion(models.Model):
    class Estados(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        CONFIRMADO = 'confirmado', 'Confirmado'
        RECHAZADO = 'rechazado', 'Rechazado'
        REEMPLAZADO = 'reemplazado', 'Reemplazado'

    id_asignacion = models.AutoField(primary_key=True)
    id_turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='asignaciones')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='asignaciones')
    estado = models.CharField(max_length=20, choices=Estados.choices, default=Estados.BORRADOR)
    asignado_automaticamente = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asignacion'
        constraints = [
            models.UniqueConstraint(
                fields=['id_turno', 'id_usuario'],
                condition=Q(estado__in=ESTADOS_ACTIVOS),
                name='uniq_asignacion_activa_por_turno',
            ),
        ]

    def __str__(self):
        return f'{self.id_usuario} -> {self.id_turno}'
