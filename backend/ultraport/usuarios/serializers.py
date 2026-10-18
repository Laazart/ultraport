from rest_framework_simplejwt.serializers import TokenObtainPairSerializer 
from .models import Usuario, Rol , Contrato
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator 

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rut'] = user.rut
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data.update({
            'usuario': {
                'id_usuario': self.user.id_usuario,
                'rut': self.user.rut,
                'nombres': self.user.nombres,
                'apellidos': self.user.apellidos,
                'correo': self.user.correo,
                'telefono': self.user.telefono,
                'estado': self.user.estado,
                'rol': self.user.id_rol.nombre_rol if self.user.id_rol else None, 
                'id_rol': self.user.id_rol_id, 
            }
        })
        return data

class SolicitarRecuperacionSerializer(serializers.Serializer):
    correo = serializers.EmailField()


class RestablecerPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value

class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    regex_celular_chile = RegexValidator(regex=r'^9\d{8}$', message="El número de celular debe tener 9 dígitos y comenzar con 9 (ej: 947492086).")
    telefono= serializers.CharField(max_length=9, validators=[regex_celular_chile],help_text="Número celular de Chile (9 dígitos, comenzando con 9)")

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'rut', 'nombres', 'apellidos', 'correo','telefono', 'id_rol', 'id_contrato', 'estado', 'fecha_creacion', 'password',]
        read_only_fields = ['id_usuario', 'fecha_creacion']# --- NUEVA VALIDACIÓN FUERTE ---
    def validate_id_rol(self, value):
        if value is not None:
            roles_permitidos = [1, 2, 3] # 5: Admin, 6: Trabajador, 7: Planificador
            
            if value.id_rol not in roles_permitidos:
                raise serializers.ValidationError("Violación de seguridad: El rol indicado no está permitido o no existe.")
        return value
    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'La contraseña es obligatoria.'})
        return attrs
    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, valor in validated_data.items():
            setattr(instance, attr, valor)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class RolSerializer(serializers.ModelSerializer):
    id_rol = serializers.IntegerField(read_only=True,help_text='Identificador del rol.',)
    nombre_rol = serializers.CharField(max_length=50,help_text='Nombre único del rol.',)
    descripcion = serializers.CharField(max_length=255,allow_null=True,required=False,allow_blank=True,help_text='Texto opcional que explica el alcance del rol.',)
    class Meta:
        model = Rol
        fields = ['id_rol', 'nombre_rol', 'descripcion',]
        read_only_fields= ['id_rol']
class ContratoSerializer(serializers.ModelSerializer):
    """Condiciones laborales: tipo, jornada y límites de fatiga."""
    id_contrato = serializers.IntegerField(read_only=True,help_text='Identificador del contrato.',)
    tipo = serializers.CharField(max_length=30,help_text='Tipo de vínculo: indefinido o eventual_por_faena.',)
    modalidad = serializers.CharField(max_length=20,allow_null=True,required=False,allow_blank=True,help_text='Ciclo de trabajo, por ejemplo 7x7 o 4x3.',)
    turno_habitual = serializers.CharField(max_length=20,help_text='Turno habitual: dia, tarde, noche o rotativo.',)
    horas_semanales_pactadas = serializers.IntegerField(help_text='Horas semanales acordadas en el contrato.',)
    permite_horas_extra = serializers.BooleanField(required=False,help_text='Indica si el contrato admite horas extra.',)
    max_noches_consecutivas = serializers.IntegerField(help_text='Tope de noches seguidas permitido para este contrato.',)
    fecha_inicio = serializers.DateField(help_text='Fecha de inicio del contrato.',)
    fecha_termino = serializers.DateField(allow_null=True,required=False,help_text='Fecha de término. Vacío si el contrato sigue vigente.',)
    fecha_creacion = serializers.DateTimeField(read_only=True, help_text='Fecha en que se creó el contrato.',)
    fecha_actualizacion = serializers.DateTimeField(read_only=True, help_text='Fecha en que se actualizo el contrato.',)
    class Meta:
        model = Contrato
        fields = ['id_contrato','tipo','modalidad','turno_habitual','horas_semanales_pactadas','permite_horas_extra','max_noches_consecutivas', 'fecha_inicio','fecha_termino',"fecha_creacion","fecha_actualizacion"]
        read_only_fields = ['id_contrato', 'fecha_creacion', 'fecha_actualizacion']