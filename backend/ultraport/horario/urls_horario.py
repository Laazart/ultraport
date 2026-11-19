from django.urls import path

from .views_horario import HorarioDiaView, HorarioSemanaView

urlpatterns = [
    path('horario/dia/', HorarioDiaView.as_view(), name='horario_dia'),
    path('horario/semana/', HorarioSemanaView.as_view(), name='horario_semana'),
]
