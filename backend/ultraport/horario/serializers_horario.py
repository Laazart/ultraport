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
    mis_turnos = MiTurnoSerializer(many=True)
    bloques = BloqueHorarioSerializer(many=True)


# ------------------------------------------------------------------ semana

class FiltroSemanaSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)


class BloqueSemanaSerializer(BloqueBaseSerializer):
    nombre = serializers.CharField()


class DiaSemanaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    malla = MallaResumenSerializer(allow_null=True)
    publicada = serializers.BooleanField()
    visible = serializers.BooleanField()


class MiTurnoSemanaSerializer(MiTurnoSerializer):
    fecha_termino = serializers.DateField()


class MiDiaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    estado = serializers.CharField()
    turnos = MiTurnoSemanaSerializer(many=True)
    sale_de_nocturno = serializers.TimeField(format=FORMATO_HORA, allow_null=True)


class FilaMatrizSerializer(serializers.Serializer):
    """Solo código y nombre: sin RUT, correo ni teléfono."""
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    turnos = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()))


class FuncionMatrizSerializer(serializers.Serializer):
    funcion = serializers.CharField()
    sin_turnos = serializers.BooleanField()
    trabajadores = FilaMatrizSerializer(many=True)


class HorarioSemanaSerializer(serializers.Serializer):
    desde = serializers.DateField()
    hasta = serializers.DateField()
    generado_en = serializers.DateTimeField(format=FORMATO_HORA)
    puede_editar = serializers.BooleanField()
    bloques = BloqueSemanaSerializer(many=True)
    dias = DiaSemanaSerializer(many=True)
    mi_semana = MiDiaSerializer(many=True, allow_null=True)
    matriz = FuncionMatrizSerializer(many=True, allow_null=True)
