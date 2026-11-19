from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import Permisos, TienePermiso
from .consultas_horario import horario_del_dia, horario_semana
from .serializers_horario import (
    FiltroFechaSerializer, FiltroSemanaSerializer, HorarioDiaSerializer, HorarioSemanaSerializer,
)


class HorarioDiaView(APIView):
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.VER_HORARIO

    def get(self, request):
        filtro = FiltroFechaSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        fecha = filtro.validated_data.get('fecha') or timezone.localdate()
        return Response(HorarioDiaSerializer(horario_del_dia(fecha, request.user)).data)


class HorarioSemanaView(APIView):
    """RF-14: semana (lunes a domingo) que contiene ?desde=; por defecto, la actual."""
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.VER_HORARIO

    def get(self, request):
        filtro = FiltroSemanaSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        desde = filtro.validated_data.get('desde') or timezone.localdate()
        return Response(HorarioSemanaSerializer(horario_semana(desde, request.user)).data)
