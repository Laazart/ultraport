from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AvisosListView, CambiarEstadoView, MisAvisosView, AsignacionViewSet, MallaViewSet, TurnoViewSet
router = DefaultRouter()
router.register('mallas', MallaViewSet, basename='mallas')
router.register('turnos', TurnoViewSet, basename='turnos')
router.register('asignaciones', AsignacionViewSet, basename='asignaciones')

urlpatterns = [
    path('inasistencias/', AvisosListView.as_view(), name='inasistencias'),
    path('inasistencias/mis-avisos/', MisAvisosView.as_view(), name='mis_inasistencias'),
    path('inasistencias/<int:pk>/estado/', CambiarEstadoView.as_view(), name='inasistencia_estado'),
    path('', include(router.urls)),
]
