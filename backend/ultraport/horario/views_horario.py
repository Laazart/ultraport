from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import Permisos, TienePermiso
from .consultas_horario import horario_del_dia
from .serializers_horario import FiltroFechaSerializer, HorarioDiaSerializer


class HorarioDiaView(APIView):
    permission_classes = [IsAuthenticated, TienePermiso]
    permiso_requerido = Permisos.VER_HORARIO

    def get(self, request):
        filtro = FiltroFechaSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        fecha = filtro.validated_data.get('fecha') or timezone.localdate()
        return Response(HorarioDiaSerializer(horario_del_dia(fecha, request.user)).data)
