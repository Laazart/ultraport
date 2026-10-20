from rest_framework import generics, status, mixins, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from usuarios.permissions import Permisos, TienePermiso
from .models import NotificacionInasistencia, Malla, Turno, Asignacion
from .serializers import CambiarEstadoSerializer, NotificacionInasistenciaSerializer
from datetime import timedelta, date
from .plantillas import PLANTILLA_1_TURNO
from .services import requerimientos_desde_plantilla
from django.utils import timezone
from rest_framework.decorators import action

from .reglas import candidatos_para_turno
from .serializers import (
    AsignacionSerializer, IniciarPlanificacionSerializer, MallaSerializer,
    ReemplazarAsignacionSerializer, TurnoSerializer,
)
from .services import (
    asignar_usuario, autocompletar_malla, iniciar_planificacion,
    publicar_malla, quitar_asignacion, reemplazar_asignacion,
)

class MisAvisosView(generics.ListCreateAPIView):
    serializer_class = NotificacionInasistenciaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.NOTIFICAR_INASISTENCIA
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return NotificacionInasistencia.objects.select_related('id_usuario').filter(
            id_usuario=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(id_usuario=self.request.user)


class AvisosListView(generics.ListAPIView):
    serializer_class = NotificacionInasistenciaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.GESTIONAR_INASISTENCIA

    def get_queryset(self):
        qs = NotificacionInasistencia.objects.select_related('id_usuario')
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class CambiarEstadoView(APIView):
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.GESTIONAR_INASISTENCIA

    def patch(self, request, pk):
        notificacion = get_object_or_404(NotificacionInasistencia, pk=pk)
        serializer = CambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notificacion.estado = serializer.validated_data['estado']
        notificacion.save(update_fields=['estado'])

        return Response(
            NotificacionInasistenciaSerializer(notificacion, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

def _manana():
    return timezone.localdate() + timedelta(days=1)


class MallaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MallaSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.PLANIFICAR_TURNOS

    def get_queryset(self):
        return (
            Malla.objects
            .prefetch_related('turnos__id_bloque', 'turnos__id_puesto', 'turnos__asignaciones__id_usuario')
            .order_by('-fecha')
        )
    @action(detail=False, methods=['post'], url_path='iniciar-plantilla')
    def iniciar_plantilla(self, request):
        fecha_str = request.data.get('fecha')
        fecha = date.fromisoformat(fecha_str) if fecha_str else _manana()
        id_bloque = int(request.data.get('id_bloque', 1))
        malla = iniciar_planificacion(
            fecha=fecha,
            requerimientos=requerimientos_desde_plantilla(id_bloque, PLANTILLA_1_TURNO),
            creado_por=request.user,
        )
        return Response(MallaSerializer(malla).data, status=status.HTTP_201_CREATED)
    @action(detail=False, methods=['post'], url_path='iniciar')
    def iniciar(self, request):
        serializer = IniciarPlanificacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        malla = iniciar_planificacion(
            fecha=serializer.validated_data.get('fecha') or _manana(),
            requerimientos=serializer.validated_data['requerimientos'],
            creado_por=request.user,
        )
        return Response(MallaSerializer(malla).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def autocompletar(self, request, pk=None):
        malla = self.get_object()
        creadas = autocompletar_malla(malla)
        return Response({'asignados': len(creadas)})

    @action(detail=True, methods=['post'])
    def publicar(self, request, pk=None):
        malla = publicar_malla(self.get_object())
        return Response(MallaSerializer(malla).data)


class TurnoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.PLANIFICAR_TURNOS

    def get_queryset(self):
        return Turno.objects.select_related('id_malla', 'id_bloque', 'id_puesto')

    @action(detail=True, methods=['get'])
    def candidatos(self, request, pk=None):
        turno = self.get_object()
        data = [
            {'id_usuario': usuario.pk, 'nombre': str(usuario), 'horas_semana': horas}
            for horas, usuario in candidatos_para_turno(turno)
        ]
        return Response(data)


class AsignacionViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Asignacion.objects.select_related('id_turno__id_malla', 'id_usuario')
    serializer_class = AsignacionSerializer
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.PLANIFICAR_TURNOS

    def perform_create(self, serializer):
        serializer.instance = asignar_usuario(
            turno=serializer.validated_data['id_turno'],
            usuario=serializer.validated_data['id_usuario'],
        )

    def perform_destroy(self, instance):
        quitar_asignacion(instance)

    @action(detail=True, methods=['post'])
    def reemplazar(self, request, pk=None):
        asignacion = self.get_object()
        serializer = ReemplazarAsignacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nueva = reemplazar_asignacion(asignacion, serializer.validated_data['id_usuario'])
        return Response(AsignacionSerializer(nueva).data)