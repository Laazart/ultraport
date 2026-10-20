from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from usuarios.models import Usuario
from .models import Malla, Turno, Asignacion, ESTADOS_ACTIVOS
from .reglas import validar_asignacion, candidatos_para_turno


def _validar_editable(malla):
    if malla.estado == Malla.Estados.PUBLICADA:
        raise ValidationError('La malla está publicada y no se puede modificar.')


def _cupos_ocupados(turno):
    return turno.asignaciones.filter(estado__in=ESTADOS_ACTIVOS).count()


@transaction.atomic
def iniciar_planificacion(fecha, requerimientos, creado_por):
    if fecha <= timezone.localdate():
        raise ValidationError('La planificación debe ser para una fecha futura.')
    if Malla.objects.filter(fecha=fecha).exists():
        raise ValidationError('Ya existe una malla para esa fecha.')

    malla = Malla.objects.create(fecha=fecha, creado_por=creado_por)
    Turno.objects.bulk_create([Turno(id_malla=malla, **req) for req in requerimientos])
    return malla


@transaction.atomic
def asignar_usuario(turno, usuario, automatica=False):
    _validar_editable(turno.id_malla)

    Usuario.objects.select_for_update().get(pk=usuario.pk)

    if _cupos_ocupados(turno) >= turno.cupos:
        raise ValidationError('El turno no tiene cupos disponibles.')

    errores = validar_asignacion(usuario, turno)
    if errores:
        raise ValidationError(errores)

    return Asignacion.objects.create(
        id_turno=turno,
        id_usuario=usuario,
        asignado_automaticamente=automatica,
    )


@transaction.atomic
def quitar_asignacion(asignacion):
    _validar_editable(asignacion.id_turno.id_malla)
    asignacion.delete()


@transaction.atomic
def reemplazar_asignacion(asignacion, nuevo_usuario):
    turno = asignacion.id_turno
    _validar_editable(turno.id_malla)

    if nuevo_usuario.pk == asignacion.id_usuario_id:
        raise ValidationError('El trabajador ya está asignado a este turno.')

    asignacion.estado = Asignacion.Estados.REEMPLAZADO
    asignacion.save(update_fields=['estado', 'fecha_actualizacion'])

    return asignar_usuario(turno, nuevo_usuario)


@transaction.atomic
def autocompletar_malla(malla):
    _validar_editable(malla)

    turnos = list(
        malla.turnos.select_related('id_bloque', 'id_puesto', 'id_maquinaria_req', 'id_tipo_licencia_req', 'id_malla')
    )
    turnos.sort(key=lambda t: len(candidatos_para_turno(t)))

    creadas = []
    for turno in turnos:
        faltan = turno.cupos - _cupos_ocupados(turno)
        if faltan <= 0:
            continue
        for _horas, usuario in candidatos_para_turno(turno)[:faltan]:
            creadas.append(asignar_usuario(turno, usuario, automatica=True))
    return creadas


@transaction.atomic
def publicar_malla(malla):
    _validar_editable(malla)

    incompletos = [t for t in malla.turnos.all() if _cupos_ocupados(t) < t.cupos]
 #   if incompletos:
 #       raise ValidationError(
 #            f'Hay {len(incompletos)} turno(s) con cupos sin cubrir. Complete la malla antes de publicar.'
 #        )

    malla.estado = Malla.Estados.PUBLICADA
    malla.save(update_fields=['estado', 'fecha_actualizacion'])
    return malla

from usuarios.models import Puesto, Maquinaria
from .models import Area, BloqueTurno
from .plantillas import PLANTILLA_1_TURNO


def requerimientos_desde_plantilla(id_bloque, plantilla=PLANTILLA_1_TURNO):
    bloque = BloqueTurno.objects.get(pk=id_bloque)
    requerimientos = []
    for area, puesto, cupos, maquina in plantilla:
        requerimientos.append({
            'id_bloque': bloque,
            'id_area': Area.objects.get(nombre_area=area),
            'id_puesto': Puesto.objects.get(nombre_puesto=puesto),
            'id_maquinaria_req': Maquinaria.objects.get(nombre_maquinaria=maquina) if maquina else None,
            'cupos': cupos,
        })
    return requerimientos