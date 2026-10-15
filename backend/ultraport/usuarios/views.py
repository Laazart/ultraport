from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, RestablecerPasswordSerializer, SolicitarRecuperacionSerializer
from rest_framework.permissions import AllowAny
from .services import crear_token_recuperacion, enviar_correo_recuperacion, validar_token
from .models import Usuario

MENSAJE_GENERICO = 'Si el correo existe, recibirás un enlace para restablecer tu contraseña. ;)'

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"mensaje": "Cierre de sesión exitoso"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class SolicitarRecuperacionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SolicitarRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = Usuario.objects.filter(correo=serializer.validated_data['correo'], estado='activo').first()
        if usuario:
            token = crear_token_recuperacion(usuario)
            enviar_correo_recuperacion(usuario, token)

        return Response({'mensaje': MENSAJE_GENERICO}, status=status.HTTP_200_OK)


class RestablecerPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RestablecerPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registro = validar_token(serializer.validated_data['token'])
        if registro is None:
            return Response(
                {'error': 'El enlace no es válido o expiró.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = registro.id_usuario
        usuario.set_password(serializer.validated_data['password'])
        usuario.save(update_fields=['password'])

        registro.usado = True
        registro.save(update_fields=['usado'])

        return Response({'mensaje': 'Contraseña actualizada.'}, status=status.HTTP_200_OK)