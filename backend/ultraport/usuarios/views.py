from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, RestablecerPasswordSerializer, SolicitarRecuperacionSerializer, UsuarioSerializer, RolSerializer, ContratoSerializer
from rest_framework.permissions import AllowAny
from .services import (
    buscar_usuario_por_identificador, crear_token_recuperacion, enviar_correo_recuperacion, validar_token,
)
from .permissions import Permisos, TienePermiso
from .models import Usuario, Rol, Contrato, Puesto, TipoLicencia, Maquinaria, UsuarioPuesto, UsuarioLicencia, UsuarioMaquinaria
from django.utils import timezone
from django.db.models import Q, Value
from django.db.models.functions import Concat
from rest_framework.pagination import PageNumberPagination
from .serializers import (
    PuestoSerializer, TipoLicenciaSerializer, MaquinariaSerializer,
    UsuarioPuestoSerializer, UsuarioLicenciaSerializer, UsuarioMaquinariaSerializer,
)
import logging

logger = logging.getLogger(__name__)

MENSAJE_GENERICO = 'Si la cuenta existe, recibirás un enlace para restablecer tu contraseña.'

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

        usuario = buscar_usuario_por_identificador(serializer.validated_data['identificador'])
        if usuario and usuario.is_active and usuario.estado == 'activo':
            token = crear_token_recuperacion(usuario)
            try:
                enviar_correo_recuperacion(usuario, token)
            except Exception:
                # La respuesta no debe cambiar: revelaría que la cuenta existe.
                logger.exception('No se pudo enviar el correo de recuperación (usuario %s)', usuario.pk)

        # Misma respuesta exista o no la cuenta (RF-05).
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

class PaginacionUsuarios(PageNumberPagination):
    """20 usuarios por página (?page=N). Agrega total de páginas y página actual."""
    page_size = 20

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data['total_paginas'] = self.page.paginator.num_pages
        response.data['pagina'] = self.page.number
        return response


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR
    pagination_class = PaginacionUsuarios

    def get_queryset(self):
        queryset = (
            Usuario.objects
            .select_related('id_rol', 'id_contrato')
            # id_usuario desempata: el orden debe ser total para paginar sin saltos.
            .order_by('apellidos', 'nombres', 'id_usuario')
        )
        if self.action == 'list':
            queryset = self._filtrar_busqueda(queryset)
        return queryset

    def _filtrar_busqueda(self, queryset):
        """?search= filtra por nombre completo o RUT (con o sin puntos)."""
        # .lower() en Python: el LIKE de SQLite solo ignora mayúsculas en ASCII,
        # así "MARÍA" encuentra "María".
        termino = self.request.query_params.get('search', '').strip().lower()
        if not termino:
            return queryset
        filtro = Q(nombre_completo__icontains=termino)
        termino_rut = termino.replace('.', '')
        if termino_rut:
            filtro |= Q(rut__icontains=termino_rut)
        return (
            queryset
            .annotate(nombre_completo=Concat('nombres', Value(' '), 'apellidos'))
            .filter(filtro)
        )

    def destroy(self, request, *args, **kwargs):
        usuario = self.get_object()
        usuario.estado = 'inactivo'
        usuario.is_active = False
        usuario.save(update_fields=['estado', 'is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

class RolViewSet(viewsets.ModelViewSet ):
    """Expone el catálogo fijo que el planificador usa al crear usuarios."""
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR

class ContratoViewSet(viewsets.ModelViewSet):
    queryset = Contrato.objects.all()
    serializer_class = ContratoSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR




class PuestoViewSet(viewsets.ModelViewSet):
    queryset = Puesto.objects.all()
    serializer_class = PuestoSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR


class TipoLicenciaViewSet(viewsets.ModelViewSet):
    queryset = TipoLicencia.objects.all()
    serializer_class = TipoLicenciaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR


class MaquinariaViewSet(viewsets.ModelViewSet):
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR


class UsuarioPuestoViewSet(viewsets.ModelViewSet):
    queryset = UsuarioPuesto.objects.all()
    serializer_class = UsuarioPuestoSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR


class UsuarioLicenciaViewSet(viewsets.ModelViewSet):
    queryset = UsuarioLicencia.objects.all()
    serializer_class = UsuarioLicenciaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR


class UsuarioMaquinariaViewSet(viewsets.ModelViewSet):
    queryset = UsuarioMaquinaria.objects.all()
    serializer_class = UsuarioMaquinariaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.USUARIOS_GESTIONAR