from rest_framework import generics, status, mixins, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from usuarios.permissions import Permisos, TienePermiso
from .models import NotificacionInasistencia, Malla, Turno, Asignacion
from datetime import timedelta, date
from .plantillas import PLANTILLA_BASE, BLOQUES_PLANTILLA
from django.utils import timezone
from rest_framework.decorators import action

from .reglas import candidatos_para_turno
from .serializers import (
    AsignacionSerializer, IniciarPlanificacionSerializer, MallaSerializer,
    ReemplazarAsignacionSerializer, TurnoSerializer, CambiarEstadoSerializer, NotificacionInasistenciaSerializer
)
from .services import (
    asignar_usuario, autocompletar_malla, iniciar_planificacion,
    publicar_malla, quitar_asignacion, reemplazar_asignacion, requerimientos_desde_plantilla
)
from .reportes import pdf_inasistencias, pdf_malla
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
        malla = iniciar_planificacion(
            fecha=fecha,
            requerimientos=requerimientos_desde_plantilla(),
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
            {
                'id_usuario': usuario.pk,
                'nombre': f'{usuario.nombres} {usuario.apellidos}',
                'rut': usuario.rut,
                'correo': usuario.correo,
                'telefono': usuario.telefono,
                'horas_semana': horas,
            }
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
class ReporteMallaPdfView(APIView):
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.REPORTES_EXPORTACION

    def get(self, request, pk):
        malla = get_object_or_404(Malla, pk=pk)
        if malla.estado != Malla.Estados.PUBLICADA:
            return Response(
                {'detail': 'Solo se puede exportar una malla publicada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return pdf_malla(malla, request.query_params.get('bloque') or None)


class ReporteInasistenciasPdfView(APIView):
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.REPORTES_EXPORTACION

    def get(self, request):
        try:
            desde = date.fromisoformat(request.query_params['desde'])
            hasta = date.fromisoformat(request.query_params['hasta'])
        except (KeyError, ValueError):
            return Response(
                {'detail': 'Indique un rango válido (desde y hasta en formato AAAA-MM-DD).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if desde > hasta:
            return Response(
                {'detail': 'La fecha "desde" no puede ser posterior a "hasta".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return pdf_inasistencias(desde, hasta, request.query_params.get('estado') or None)