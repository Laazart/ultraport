from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import NotificacionInasistencia
from .permissions import EsEncargado, es_encargado
from .serializers import CambiarEstadoSerializer, NotificacionInasistenciaSerializer


class NotificacionListCreateView(generics.ListCreateAPIView):
    """el trabajador ve sus propios avisos
    el encargado ve todos los avisos (filtro opcional ?estado=).
    el trabajador registra un aviso, de forma predeterminada viene como pendiente"""
    serializer_class = NotificacionInasistenciaSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = NotificacionInasistencia.objects.select_related('id_usuario')
        if not es_encargado(self.request.user):
            qs = qs.filter(id_usuario=self.request.user)
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def perform_create(self, serializer):
        serializer.save(id_usuario=self.request.user)


class CambiarEstadoView(APIView):
    """encargado puede aprobar, rechazar o devolver a pendiente un aviso"""
    permission_classes = [IsAuthenticated, EsEncargado]

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
