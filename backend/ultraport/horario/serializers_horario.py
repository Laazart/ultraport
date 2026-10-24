from rest_framework import serializers

FORMATO_HORA = '%H:%M'


class FiltroFechaSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False)


class TrabajadorHorarioSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    funcion = serializers.CharField()
    maquina = serializers.CharField(allow_null=True)
    es_mio = serializers.BooleanField()


class FaenaHorarioSerializer(serializers.Serializer):
    faena = serializers.CharField()
    trabajadores = TrabajadorHorarioSerializer(many=True)


class AreaHorarioSerializer(serializers.Serializer):
    area = serializers.CharField()
    faenas = FaenaHorarioSerializer(many=True)


class BloqueBaseSerializer(serializers.Serializer):
    id_bloque = serializers.IntegerField()
    orden = serializers.IntegerField()
    hora_inicio = serializers.TimeField(format=FORMATO_HORA)
    hora_termino = serializers.TimeField(format=FORMATO_HORA)
    cruza_medianoche = serializers.BooleanField()


class BloqueHorarioSerializer(BloqueBaseSerializer):
    nombre = serializers.CharField()
    total = serializers.IntegerField()
    areas = AreaHorarioSerializer(many=True)


class MiTurnoSerializer(BloqueBaseSerializer):
    area = serializers.CharField()
    funcion = serializers.CharField()
    maquina = serializers.CharField(allow_null=True)


class MallaResumenSerializer(serializers.Serializer):
    id_malla = serializers.IntegerField()
    estado = serializers.CharField()


class HorarioDiaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    generado_en = serializers.DateTimeField(format=FORMATO_HORA)
    malla = MallaResumenSerializer(allow_null=True)
    publicada = serializers.BooleanField()
    puede_editar = serializers.BooleanField()
    mi_turno = MiTurnoSerializer(allow_null=True)
    bloques = BloqueHorarioSerializer(many=True)
