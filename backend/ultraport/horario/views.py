from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from usuarios.permissions import Permisos, TienePermiso

from .models import NotificacionInasistencia
from .serializers import CambiarEstadoSerializer, NotificacionInasistenciaSerializer


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
