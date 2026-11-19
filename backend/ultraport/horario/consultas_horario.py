from datetime import timedelta

from django.utils import timezone

from usuarios.models import Usuario
from usuarios.permissions import PERMISOS_POR_ROL, Permisos, Roles
from .models import ESTADOS_ACTIVOS, Asignacion, BloqueTurno, Malla

FAENA_GENERAL = 'General'
SIN_AREA = 'Sin área'
SIN_TURNOS = 'Sin turnos esta semana'
DIAS_SEMANA = 7

# Estado de cada día en "Mi semana".
DIA_SIN_MALLA = 'sin_malla'
DIA_NO_PUBLICADA = 'no_publicada'
DIA_TURNO = 'turno'
DIA_DESCANSO = 'descanso'

_SELECT_ASIGNACION = (
    'id_usuario',
    'id_turno__id_malla',
    'id_turno__id_bloque',
    'id_turno__id_area',
    'id_turno__id_puesto',
    'id_turno__id_maquinaria_req',
)


def _puede_planificar(usuario):
    return Permisos.PLANIFICAR_TURNOS in PERMISOS_POR_ROL.get(usuario.id_rol_id, set())


def _visible(malla, puede_editar):
    """Publicada para todos; un borrador solo para quien puede planificar."""
    return malla is not None and (malla.estado == Malla.Estados.PUBLICADA or puede_editar)


def _asignaciones_visibles(malla, puede_editar):
    if not _visible(malla, puede_editar):
        return []
    return (
        Asignacion.objects
        .filter(id_turno__id_malla=malla, estado__in=ESTADOS_ACTIVOS)
        .select_related(*_SELECT_ASIGNACION)
    )


def _datos_bloque(bloque):
    return {
        'id_bloque': bloque.id_bloque,
        'orden': bloque.orden_secuencia,
        'hora_inicio': bloque.hora_inicio,
        'hora_termino': bloque.hora_termino,
        'cruza_medianoche': bloque.es_nocturno,
    }


def _area_de(turno):
    return turno.id_area.nombre_area if turno.id_area else SIN_AREA


def _maquina_de(turno):
    return turno.id_maquinaria_req.nombre_maquinaria if turno.id_maquinaria_req else None


def _nombre(usuario):
    return f'{usuario.nombres} {usuario.apellidos}'


def _mi_turno(turno):
    """Turno propio: horario del bloque + área, función y máquina."""
    return {
        **_datos_bloque(turno.id_bloque),
        'area': _area_de(turno),
        'funcion': turno.id_puesto.nombre_puesto,
        'maquina': _maquina_de(turno),
    }


def _orden_area(nombre):
    return (nombre == SIN_AREA, nombre.lower())


def _orden_turno(turno):
    return (turno['orden'], _orden_area(turno['area']))


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
    mis_turnos = []
    for asignacion in _asignaciones_visibles(malla, puede_editar):
        turno = asignacion.id_turno
        trabajador = asignacion.id_usuario
        fila = {
            'codigo': str(trabajador.pk),
            'nombre': _nombre(trabajador),
            'funcion': turno.id_puesto.nombre_puesto,
            'maquina': _maquina_de(turno),
            'es_mio': trabajador.pk == usuario.pk,
        }
        filas_por_bloque[turno.id_bloque_id].setdefault(_area_de(turno), []).append(fila)

        if fila['es_mio'] and es_trabajador:
            mis_turnos.append(_mi_turno(turno))

    mis_turnos.sort(key=_orden_turno)

    return {
        'fecha': fecha,
        'generado_en': timezone.localtime(),
        'malla': malla,
        'publicada': malla is not None and malla.estado == Malla.Estados.PUBLICADA,
        'puede_editar': puede_editar,
        'mis_turnos': mis_turnos,
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


# ------------------------------------------------------------------ semana

def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def _mi_semana(fechas, mallas, asignaciones):
    """Siete días del trabajador: sus turnos, descansos y salida de nocturno."""
    turnos_por_fecha = {}
    for asignacion in asignaciones:
        turno = asignacion.id_turno
        fecha = turno.id_malla.fecha
        _, fin = turno.id_bloque.intervalo(fecha)
        turnos_por_fecha.setdefault(fecha, []).append({**_mi_turno(turno), 'fecha_termino': fin.date()})

    dias = []
    for fecha in fechas:
        malla = mallas.get(fecha)
        turnos = sorted(turnos_por_fecha.get(fecha, []), key=_orden_turno)
        if malla is None:
            estado = DIA_SIN_MALLA
        elif malla.estado != Malla.Estados.PUBLICADA:
            estado = DIA_NO_PUBLICADA
        elif turnos:
            estado = DIA_TURNO
        else:
            estado = DIA_DESCANSO

        nocturnos_previos = [
            t for t in turnos_por_fecha.get(fecha - timedelta(days=1), [])
            if t['fecha_termino'] == fecha
        ]
        dias.append({
            'fecha': fecha,
            'estado': estado,
            'turnos': turnos,
            'sale_de_nocturno': min((t['hora_termino'] for t in nocturnos_previos), default=None),
        })
    return dias


def _matriz(lunes, asignaciones, sin_turnos):
    """Filas (función, trabajador) con los turnos de cada día; al final, quienes no tienen turnos."""
    filas = {}
    for asignacion in asignaciones:
        turno = asignacion.id_turno
        indice = (turno.id_malla.fecha - lunes).days
        if not 0 <= indice < DIAS_SEMANA:
            continue
        trabajador = asignacion.id_usuario
        funcion = turno.id_puesto.nombre_puesto
        fila = filas.setdefault((funcion, trabajador.pk), {
            'codigo': str(trabajador.pk),
            'nombre': _nombre(trabajador),
            'turnos': [set() for _ in range(DIAS_SEMANA)],
        })
        fila['turnos'][indice].add(turno.id_bloque.orden_secuencia)

    por_funcion = {}
    for (funcion, _), fila in filas.items():
        fila['turnos'] = [sorted(dia) for dia in fila['turnos']]
        por_funcion.setdefault(funcion, []).append(fila)

    grupos = [
        {
            'funcion': funcion,
            'sin_turnos': False,
            'trabajadores': sorted(por_funcion[funcion], key=lambda f: int(f['codigo'])),
        }
        for funcion in sorted(por_funcion, key=str.lower)
    ]
    if sin_turnos:
        grupos.append({
            'funcion': SIN_TURNOS,
            'sin_turnos': True,
            'trabajadores': [
                {'codigo': str(u.pk), 'nombre': _nombre(u), 'turnos': [[] for _ in range(DIAS_SEMANA)]}
                for u in sin_turnos
            ],
        })
    return grupos


def _trabajadores_sin_turnos(con_turnos):
    """Trabajadores activos sin asignaciones visibles en la semana (una consulta)."""
    return list(
        Usuario.objects
        .filter(id_rol_id=Roles.TRABAJADOR, is_active=True, estado='activo')
        .exclude(pk__in=con_turnos)
        .only('id_usuario', 'nombres', 'apellidos')
        .order_by('id_usuario')
    )


def horario_semana(desde, usuario):
    """Semana (lunes a domingo) que contiene `desde`.

    Trabajador: solo sus propios turnos (`mi_semana`); los datos ajenos ni se
    consultan. Encargado y administrador: matriz por función (`matriz`).
    Consultas constantes: 3 para el trabajador y 4 para encargado y administrador.
    """
    lunes = lunes_de(desde)
    fechas = [lunes + timedelta(days=i) for i in range(DIAS_SEMANA)]
    domingo_previo = lunes - timedelta(days=1)
    puede_editar = _puede_planificar(usuario)
    es_trabajador = usuario.id_rol_id == Roles.TRABAJADOR

    mallas = {m.fecha: m for m in Malla.objects.filter(fecha__range=(domingo_previo, fechas[-1]))}
    bloques = list(BloqueTurno.objects.all())

    # El domingo previo solo interesa al trabajador (turno nocturno que termina el lunes).
    fechas_consulta = ([domingo_previo] if es_trabajador else []) + fechas
    ids_visibles = [
        mallas[f].pk for f in fechas_consulta if _visible(mallas.get(f), puede_editar)
    ]
    asignaciones = (
        Asignacion.objects
        .filter(id_turno__id_malla__in=ids_visibles, estado__in=ESTADOS_ACTIVOS)
        .select_related(*_SELECT_ASIGNACION)
    )
    if es_trabajador:
        asignaciones = asignaciones.filter(id_usuario=usuario)
    asignaciones = list(asignaciones) if ids_visibles else []

    if es_trabajador:
        mi_semana, matriz = _mi_semana(fechas, mallas, asignaciones), None
    else:
        con_turnos = {a.id_usuario_id for a in asignaciones}
        mi_semana, matriz = None, _matriz(lunes, asignaciones, _trabajadores_sin_turnos(con_turnos))

    return {
        'desde': lunes,
        'hasta': fechas[-1],
        'generado_en': timezone.localtime(),
        'puede_editar': puede_editar,
        'bloques': [{**_datos_bloque(b), 'nombre': b.nombre_bloque} for b in bloques],
        'dias': [
            {
                'fecha': f,
                'malla': mallas.get(f),
                'publicada': mallas.get(f) is not None and mallas[f].estado == Malla.Estados.PUBLICADA,
                'visible': _visible(mallas.get(f), puede_editar),
            }
            for f in fechas
        ],
        'mi_semana': mi_semana,
        'matriz': matriz,
    }
