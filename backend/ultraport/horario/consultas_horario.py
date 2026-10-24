from django.utils import timezone

from usuarios.permissions import PERMISOS_POR_ROL, Permisos, Roles
from .models import ESTADOS_ACTIVOS, Asignacion, BloqueTurno, Malla

FAENA_GENERAL = 'General'
SIN_AREA = 'Sin área'


def _puede_planificar(usuario):
    return Permisos.PLANIFICAR_TURNOS in PERMISOS_POR_ROL.get(usuario.id_rol_id, set())


def _asignaciones_visibles(malla, puede_editar):
    if malla is None:
        return []
    if malla.estado != Malla.Estados.PUBLICADA and not puede_editar:
        return []
    return (
        Asignacion.objects
        .filter(id_turno__id_malla=malla, estado__in=ESTADOS_ACTIVOS)
        .select_related(
            'id_usuario',
            'id_turno__id_bloque',
            'id_turno__id_area',
            'id_turno__id_puesto',
            'id_turno__id_maquinaria_req',
        )
    )


def _datos_bloque(bloque):
    return {
        'id_bloque': bloque.id_bloque,
        'orden': bloque.orden_secuencia,
        'hora_inicio': bloque.hora_inicio,
        'hora_termino': bloque.hora_termino,
        'cruza_medianoche': bloque.es_nocturno,
    }


def _orden_area(nombre):
    return (nombre == SIN_AREA, nombre.lower())


def _areas(filas_por_area):
    return [
        {
            'area': area,
            'faenas': [{
                'faena': FAENA_GENERAL,
                'trabajadores': sorted(filas_por_area[area], key=lambda fila: int(fila['codigo'])),
            }],
        }
        for area in sorted(filas_por_area, key=_orden_area)
    ]


def horario_del_dia(fecha, usuario):
    malla = Malla.objects.filter(fecha=fecha).first()
    bloques = list(BloqueTurno.objects.all())
    puede_editar = _puede_planificar(usuario)
    es_trabajador = usuario.id_rol_id == Roles.TRABAJADOR

    filas_por_bloque = {bloque.id_bloque: {} for bloque in bloques}
    mi_turno = None
    for asignacion in _asignaciones_visibles(malla, puede_editar):
        turno = asignacion.id_turno
        bloque = turno.id_bloque
        trabajador = asignacion.id_usuario
        area = turno.id_area.nombre_area if turno.id_area else SIN_AREA
        fila = {
            'codigo': str(trabajador.pk),
            'nombre': f'{trabajador.nombres} {trabajador.apellidos}',
            'funcion': turno.id_puesto.nombre_puesto,
            'maquina': turno.id_maquinaria_req.nombre_maquinaria if turno.id_maquinaria_req else None,
            'es_mio': trabajador.pk == usuario.pk,
        }
        filas_por_bloque[bloque.id_bloque].setdefault(area, []).append(fila)

        if fila['es_mio'] and es_trabajador and (mi_turno is None or bloque.orden_secuencia < mi_turno['orden']):
            mi_turno = {
                **_datos_bloque(bloque),
                'area': area,
                'funcion': fila['funcion'],
                'maquina': fila['maquina'],
            }

    return {
        'fecha': fecha,
        'generado_en': timezone.localtime(),
        'malla': malla,
        'publicada': malla is not None and malla.estado == Malla.Estados.PUBLICADA,
        'puede_editar': puede_editar,
        'mi_turno': mi_turno,
        'bloques': [
            {
                **_datos_bloque(bloque),
                'nombre': bloque.nombre_bloque,
                'total': sum(len(filas) for filas in filas_por_bloque[bloque.id_bloque].values()),
                'areas': _areas(filas_por_bloque[bloque.id_bloque]),
            }
            for bloque in bloques
        ],
    }
