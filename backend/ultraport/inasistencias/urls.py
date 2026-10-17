from django.urls import path
from .views import CambiarEstadoView, NotificacionListCreateView

urlpatterns = [
    path('inasistencias/', NotificacionListCreateView.as_view(), name='inasistencias'),
    path('inasistencias/<int:pk>/estado/', CambiarEstadoView.as_view(), name='inasistencia_estado'),
]
