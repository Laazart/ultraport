from django.urls import path
from .views import AvisosListView, CambiarEstadoView, MisAvisosView

urlpatterns = [
    path('inasistencias/', AvisosListView.as_view(), name='inasistencias'),
    path('inasistencias/mis-avisos/', MisAvisosView.as_view(), name='mis_inasistencias'),
    path('inasistencias/<int:pk>/estado/', CambiarEstadoView.as_view(), name='inasistencia_estado'),
]
