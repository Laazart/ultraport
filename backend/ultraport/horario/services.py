from django.db import transaction
from django.utils import timezone
from django.conf import settings
from rest_framework.exceptions import ValidationError
from auditoria.acciones import Acciones, Entidades
from auditoria.services import registrar
from usuarios.models import Usuario
from .models import Malla, Turno, Asignacion, ESTADOS_ACTIVOS, Area, BloqueTurno, NotificacionInasistencia
from .reglas import validar_asignacion, candidatos_para_turno
from .plantillas import PLANTILLA_BASE, BLOQUES_PLANTILLA
from usuarios.models import Puesto, Maquinaria

# Cada servicio público recibe `actor` (obligatorio, keyword) y registra la
# acción en auditoría dentro de su propia transacción: si la acción falla, no
# queda registro.


def _validar_no_publicada(malla):
    if malla.estado == Malla.Estados.PUBLICADA:
        raise ValidationError('La malla ya está publicada.')


def _esta_publicada(malla):
    return malla.estado == Malla.Estados.PUBLICADA


def _estado_inicial(malla):
    """En una malla publicada las asignaciones nuevas nacen confirmadas."""
    if _esta_publicada(malla):
        return Asignacion.Estados.CONFIRMADO
    return Asignacion.Estados.BORRADOR


def _cupos_ocupados(turno):
    return turno.asignaciones.filter(estado__in=ESTADOS_ACTIVOS).count()


def _detalle_asignacion(asignacion):
    return {
        'usuario': asignacion.id_usuario_id,
        'turno': asignacion.id_turno_id,
        'malla': asignacion.id_turno.id_malla_id,
    }


@transaction.atomic
def iniciar_planificacion(fecha, requerimientos, creado_por, plantilla=False):
    if fecha <= timezone.localdate():
        raise ValidationError('La planificación debe ser para una fecha futura.')
    if Malla.objects.filter(fecha=fecha).exists():
        raise ValidationError('Ya existe una malla para esa fecha.')

    malla = Malla.objects.create(fecha=fecha, creado_por=creado_por)
    Turno.objects.bulk_create([Turno(id_malla=malla, **req) for req in requerimientos])
    registrar(creado_por, Acciones.MALLA_INICIAR, Entidades.MALLA, malla.pk, {
        'fecha': fecha, 'turnos': len(requerimientos), 'plantilla': plantilla,
    })
    return malla


def _crear_asignacion(turno, usuario, automatica=False):
    """Valida y crea la asignación, sin auditar (lo hace el servicio que la usa)."""
    # Los cupos son solo referencia: la asignación nunca se bloquea por cupo.
    Usuario.objects.select_for_update().get(pk=usuario.pk)

    errores = validar_asignacion(usuario, turno)
    if errores:
        raise ValidationError(errores)

    return Asignacion.objects.create(
        id_turno=turno,
        id_usuario=usuario,
        estado=_estado_inicial(turno.id_malla),
        asignado_automaticamente=automatica,
    )


@transaction.atomic
def asignar_usuario(turno, usuario, *, actor):
    asignacion = _crear_asignacion(turno, usuario)
    registrar(actor, Acciones.ASIGNACION_ASIGNAR, Entidades.ASIGNACION, asignacion.pk,
              _detalle_asignacion(asignacion))
    return asignacion


def _marcar_reemplazada(asignacion):
    asignacion.estado = Asignacion.Estados.REEMPLAZADO
    asignacion.save(update_fields=['estado', 'fecha_actualizacion'])


@transaction.atomic
def quitar_asignacion(asignacion, *, actor):
    """En borrador se elimina; en una malla publicada queda como historial (reemplazado)."""
    id_asignacion = asignacion.pk
    detalle = _detalle_asignacion(asignacion)
    if _esta_publicada(asignacion.id_turno.id_malla):
        _marcar_reemplazada(asignacion)
        detalle['modo'] = 'reemplazada'
    else:
        asignacion.delete()
        detalle['modo'] = 'eliminada'
    registrar(actor, Acciones.ASIGNACION_QUITAR, Entidades.ASIGNACION, id_asignacion, detalle)


@transaction.atomic
def mover_asignacion(asignacion, turno_destino, *, actor):
    origen = asignacion.id_turno
    if turno_destino.id_malla_id != origen.id_malla_id:
        raise ValidationError('Solo se puede mover a un turno de la misma malla.')
    if turno_destino.pk == origen.pk:
        raise ValidationError('El trabajador ya está en ese turno.')

    usuario = asignacion.id_usuario
    Usuario.objects.select_for_update().get(pk=usuario.pk)

    # El turno de origen no cuenta para traslape, descanso, horas ni noches.
    errores = validar_asignacion(usuario, turno_destino, excluir_id=asignacion.pk)
    if errores:
        raise ValidationError(errores)

    if _esta_publicada(origen.id_malla):
        _marcar_reemplazada(asignacion)
        resultado = Asignacion.objects.create(
            id_turno=turno_destino,
            id_usuario=usuario,
            estado=Asignacion.Estados.CONFIRMADO,
        )
    else:
        asignacion.id_turno = turno_destino
        asignacion.save(update_fields=['id_turno', 'fecha_actualizacion'])
        resultado = asignacion

    registrar(actor, Acciones.ASIGNACION_MOVER, Entidades.ASIGNACION, resultado.pk, {
        'usuario': usuario.pk, 'malla': origen.id_malla_id,
        'turno_origen': origen.pk, 'turno_destino': turno_destino.pk,
        'asignacion_anterior': asignacion.pk if resultado.pk != asignacion.pk else None,
    })
    return resultado


@transaction.atomic
def reemplazar_asignacion(asignacion, nuevo_usuario, *, actor):
    turno = asignacion.id_turno

    if nuevo_usuario.pk == asignacion.id_usuario_id:
        raise ValidationError('El trabajador ya está asignado a este turno.')

    _marcar_reemplazada(asignacion)
    nueva = _crear_asignacion(turno, nuevo_usuario)
    registrar(actor, Acciones.ASIGNACION_REEMPLAZAR, Entidades.ASIGNACION, nueva.pk, {
        'turno': turno.pk, 'malla': turno.id_malla_id,
        'usuario_anterior': asignacion.id_usuario_id, 'usuario_nuevo': nuevo_usuario.pk,
        'asignacion_anterior': asignacion.pk,
    })
    return nueva


@transaction.atomic
def autocompletar_malla(malla, *, actor):
    """
    Reparte por rondas: en cada pasada asigna a lo más un trabajador por turno,
    así el pool de cada puesto se distribuye entre los tres bloques. Los cupos
    son el objetivo. Nunca asigna dos turnos el mismo día a un trabajador; si el
    pool no alcanza, deja cupos pendientes (doblar turno solo es manual).
    """
    turnos = list(
        malla.turnos
        .select_related('id_bloque', 'id_puesto', 'id_maquinaria_req', 'id_tipo_licencia_req', 'id_malla')
        .order_by('id_area__nombre_area', 'id_bloque__orden_secuencia', 'id_puesto_id', 'id_turno')
    )
    pendientes = {t.pk: t.cupos - _cupos_ocupados(t) for t in turnos}
    ocupados_hoy = set(
        Asignacion.objects
        .filter(id_turno__id_malla=malla, estado__in=ESTADOS_ACTIVOS)
        .values_list('id_usuario_id', flat=True)
    )

    creadas = []
    hubo_avance = True
    while hubo_avance:
        hubo_avance = False
        for turno in turnos:
            if pendientes[turno.pk] <= 0:
                continue
            elegido = next(
                (u for _horas, u in candidatos_para_turno(turno) if u.pk not in ocupados_hoy),
                None,
            )
            if elegido is None:
                pendientes[turno.pk] = 0
                continue
            creadas.append(_crear_asignacion(turno, elegido, automatica=True))
            ocupados_hoy.add(elegido.pk)
            pendientes[turno.pk] -= 1
            hubo_avance = True

    # Un solo registro con el resumen, no uno por asignación.
    registrar(actor, Acciones.MALLA_AUTOCOMPLETAR, Entidades.MALLA, malla.pk, {
        'fecha': malla.fecha, 'asignados': len(creadas),
    })
    return creadas


@transaction.atomic
def publicar_malla(malla, exigir_cupos=None, *, actor):
    _validar_no_publicada(malla)
    if exigir_cupos is None:
        exigir_cupos = settings.HORARIO_EXIGIR_CUPOS_COMPLETOS
    if exigir_cupos:
        incompletos = [t for t in malla.turnos.all() if _cupos_ocupados(t) < t.cupos]
        if incompletos:
            raise ValidationError(
                f'Hay {len(incompletos)} turno(s) con cupos sin cubrir. Complete la malla antes de publicar.'
            )
    confirmadas = Asignacion.objects.filter(
        id_turno__id_malla=malla,
        estado=Asignacion.Estados.BORRADOR,
    ).update(estado=Asignacion.Estados.CONFIRMADO)

    malla.estado = Malla.Estados.PUBLICADA
    malla.save(update_fields=['estado', 'fecha_actualizacion'])
    registrar(actor, Acciones.MALLA_PUBLICAR, Entidades.MALLA, malla.pk, {
        'fecha': malla.fecha, 'asignaciones_confirmadas': confirmadas,
    })
    return malla


# --- Inasistencias ---

@transaction.atomic
def crear_inasistencia(datos, *, actor):
    """Aviso de inasistencia del propio trabajador (el usuario sale de la sesión, no del body)."""
    notificacion = NotificacionInasistencia.objects.create(id_usuario=actor, **datos)
    # Sin motivo ni adjunto: pueden contener datos de salud.
    registrar(actor, Acciones.INASISTENCIA_CREAR, Entidades.INASISTENCIA, notificacion.pk, {
        'trabajador': actor.pk,
        'fecha_inicio': notificacion.fecha_inicio,
        'fecha_fin': notificacion.fecha_fin,
    })
    return notificacion


@transaction.atomic
def cambiar_estado_inasistencia(notificacion, estado, *, actor):
    anterior = notificacion.estado
    notificacion.estado = estado
    notificacion.save(update_fields=['estado'])
    registrar(actor, Acciones.INASISTENCIA_ESTADO, Entidades.INASISTENCIA, notificacion.pk, {
        'trabajador': notificacion.id_usuario_id, 'de': anterior, 'a': estado,
    })
    return notificacion


def requerimientos_desde_plantilla(plantilla=PLANTILLA_BASE, bloques=BLOQUES_PLANTILLA):
    requerimientos = []
    areas = {a.nombre_area: a for a in Area.objects.all()}
    puestos = {p.nombre_puesto: p for p in Puesto.objects.all()}
    maquinas = {m.nombre_maquinaria: m for m in Maquinaria.objects.all()}
    for id_bloque in bloques:
        bloque = BloqueTurno.objects.get(pk=id_bloque)
        for area, puesto, cupos, maquina in plantilla:
            requerimientos.append({
                'id_bloque': bloque,
                'id_area': areas[area],
                'id_puesto': puestos[puesto],
                'id_maquinaria_req': maquinas[maquina] if maquina else None,
                'cupos': cupos,
            })
    return requerimientos
