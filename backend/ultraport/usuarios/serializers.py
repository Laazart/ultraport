from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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