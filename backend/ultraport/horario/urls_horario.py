from django.urls import path

from .views_horario import HorarioDiaView

urlpatterns = [
    path('horario/dia/', HorarioDiaView.as_view(), name='horario_dia'),
]
