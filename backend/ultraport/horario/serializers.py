from rest_framework import serializers
from .models import NotificacionInasistencia, BloqueTurno, Malla, Turno, Asignacion
from rest_framework import serializers

from usuarios.models import Usuario

EXTENSIONES_ADJUNTO = ('.jpg', '.jpeg', '.png', '.pdf')
TAMANO_MAX_ADJUNTO = 5 * 1024 * 1024


class NotificacionInasistenciaSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = NotificacionInasistencia
        fields = [
            'id_notificacion', 'id_usuario', 'usuario', 'id_turno', 'motivo',
            'fecha_inicio', 'fecha_fin', 'url_adjunto', 'estado', 'fecha_registro',
        ]
        read_only_fields = ['id_notificacion', 'id_usuario', 'estado', 'fecha_registro']

    def get_usuario(self, obj):
        u = obj.id_usuario
        return {
            'rut': u.rut, 'nombres': u.nombres, 'apellidos': u.apellidos,
            'correo': u.correo, 'telefono': u.telefono,
        }

    def validate_motivo(self, value):
        if not value.strip():
            raise serializers.ValidationError('El motivo es obligatorio.')
        return value.strip()

    def validate_url_adjunto(self, archivo):
        if archivo is None:
            return archivo
        if not archivo.name.lower().endswith(EXTENSIONES_ADJUNTO):
            raise serializers.ValidationError('Solo se permiten archivos JPG, PNG o PDF.')
        if archivo.size > TAMANO_MAX_ADJUNTO:
            raise serializers.ValidationError('El archivo no puede superar los 5 MB.')
        return archivo

    def validate(self, attrs):
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {'fecha_fin': 'La fecha de término no puede ser anterior a la de inicio.'}
            )
        return attrs


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=NotificacionInasistencia.ESTADOS)

class BloqueTurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloqueTurno
        fields = ['id_bloque', 'nombre_bloque', 'hora_inicio', 'hora_termino', 'orden_secuencia']


class AsignacionSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    rut = serializers.SerializerMethodField()
    correo = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    contrato = serializers.SerializerMethodField()
    maquina = serializers.SerializerMethodField()
    especialidad = serializers.SerializerMethodField()

    class Meta:
        model = Asignacion
        fields = [
            'id_asignacion', 'id_turno', 'id_usuario', 'usuario_nombre',
            'rut', 'correo', 'telefono', 'contrato',
            'maquina', 'especialidad',
            'estado', 'asignado_automaticamente',
        ]
        read_only_fields = ['estado', 'asignado_automaticamente']

    def get_usuario_nombre(self, obj):
        u = obj.id_usuario
        return f'{u.nombres} {u.apellidos}'

    def get_rut(self, obj):
        return obj.id_usuario.rut

    def get_correo(self, obj):
        return obj.id_usuario.correo

    def get_telefono(self, obj):
        return obj.id_usuario.telefono or None

    def get_contrato(self, obj):
        c = obj.id_usuario.id_contrato
        return c.get_tipo_display() if c else None

    def get_maquina(self, obj):
        maquinas = obj.id_usuario.maquinarias.select_related('id_maquinaria')
        nombres = [um.id_maquinaria.nombre_maquinaria for um in maquinas]
        return ', '.join(nombres) or None

    def get_especialidad(self, obj):
        licencias = obj.id_usuario.licencias.all()
        especialidades = [l.especialidades for l in licencias if l.especialidades]
        return ', '.join(especialidades) or None

class TurnoSerializer(serializers.ModelSerializer):
    bloque = BloqueTurnoSerializer(source='id_bloque', read_only=True)
    puesto = serializers.CharField(source='id_puesto.nombre_puesto', read_only=True)
    area = serializers.CharField(source='id_area.nombre_area', read_only=True)
    asignaciones = serializers.SerializerMethodField()

    class Meta:
        model = Turno
        fields = [
            'id_turno', 'id_bloque', 'id_area', 'area', 'id_puesto', 'puesto',
            'id_maquinaria_req', 'id_tipo_licencia_req', 'cupos',
            'bloque', 'asignaciones',
        ]

    def get_asignaciones(self, obj):
        activas = obj.asignaciones.filter(estado__in=['borrador', 'confirmado'])
        return AsignacionSerializer(activas, many=True).data
class RequerimientoTurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Turno
        fields = ['id_area', 'id_bloque', 'id_puesto', 'id_maquinaria_req', 'id_tipo_licencia_req', 'cupos']


class MallaSerializer(serializers.ModelSerializer):
    turnos = TurnoSerializer(many=True, read_only=True)

    class Meta:
        model = Malla
        fields = ['id_malla', 'fecha', 'estado', 'turnos']


class IniciarPlanificacionSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False, help_text='Por defecto, mañana.')
    requerimientos = RequerimientoTurnoSerializer(many=True, allow_empty=False)


class ReemplazarAsignacionSerializer(serializers.Serializer):
    id_usuario = serializers.PrimaryKeyRelatedField(queryset=Usuario.objects.all())