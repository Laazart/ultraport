from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AvisosListView, CambiarEstadoView, MisAvisosView, AsignacionViewSet, MallaViewSet, TurnoViewSet,MallasPublicadasView, ReporteInasistenciasView, ReporteMallaView
router = DefaultRouter()
router.register('mallas', MallaViewSet, basename='mallas')
router.register('turnos', TurnoViewSet, basename='turnos')
router.register('asignaciones', AsignacionViewSet, basename='asignaciones')

urlpatterns = [
    path('inasistencias/', AvisosListView.as_view(), name='inasistencias'),
    path('inasistencias/mis-avisos/', MisAvisosView.as_view(), name='mis_inasistencias'),
    path('inasistencias/<int:pk>/estado/', CambiarEstadoView.as_view(), name='inasistencia_estado'),
    path('reportes/mallas/', MallasPublicadasView.as_view(), name='reporte-mallas'),
    path('reportes/malla/<int:pk>/pdf/', ReporteMallaView.as_view(formato='pdf'), name='reporte-malla-pdf'),
    path('reportes/malla/<int:pk>/xlsx/', ReporteMallaView.as_view(formato='xlsx'), name='reporte-malla-xlsx'),
    path('reportes/inasistencias/pdf/', ReporteInasistenciasView.as_view(formato='pdf'), name='reporte-inasistencias-pdf'),
    path('reportes/inasistencias/xlsx/', ReporteInasistenciasView.as_view(formato='xlsx'), name='reporte-inasistencias-xlsx'),

    path('', include(router.urls)),
]
