from rest_framework_simplejwt.serializers import TokenObtainPairSerializer 
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

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
                'estado': self.user.estado,
                'rol': self.user.id_rol.nombre_rol if self.user.id_rol else None,  

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