from rest_framework import serializers
from .models import NotificacionInasistencia

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
        #estado solo lo cambia el encargado
        read_only_fields = ['id_notificacion', 'id_usuario', 'estado', 'fecha_registro']

    def get_usuario(self, obj):
        u = obj.id_usuario
        return {'rut': u.rut, 'nombres': u.nombres, 'apellidos': u.apellidos}

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
