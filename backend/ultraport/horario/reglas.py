from datetime import timedelta

from django.conf import settings
from django.db.models import Q

from usuarios.models import Usuario, UsuarioPuesto, UsuarioLicencia, UsuarioMaquinaria
from usuarios.permissions import Roles
from .models import Asignacion, ESTADOS_ACTIVOS

VENTANA_RACHA_DIAS = 14

def asignaciones_activas(usuario, desde, hasta, excluir_id=None):
    qs = (
        Asignacion.objects
        .filter(
            id_usuario=usuario,
            estado__in=ESTADOS_ACTIVOS,
            id_turno__id_malla__fecha__range=(desde, hasta),
        )
        .select_related('id_turno__id_malla', 'id_turno__id_bloque')
    )
    if excluir_id is not None:
        qs = qs.exclude(pk=excluir_id)
    return qs


def asignaciones_de_la_semana(usuario, fecha, excluir_id=None):
    lunes = fecha - timedelta(days=fecha.weekday())
    domingo = lunes + timedelta(days=6)
    return list(asignaciones_activas(usuario, lunes, domingo, excluir_id))


def horas_de_la_semana(usuario, fecha, excluir_id=None):
    return sum(
        a.id_turno.id_bloque.duracion_horas()
        for a in asignaciones_de_la_semana(usuario, fecha, excluir_id)
    )
def _largo_racha_nocturna(usuario, fecha, excluir_id=None):
    desde = fecha - timedelta(days=VENTANA_RACHA_DIAS)
    hasta = fecha + timedelta(days=VENTANA_RACHA_DIAS)
    noches = {
        a.id_turno.id_malla.fecha
        for a in asignaciones_activas(usuario, desde, hasta, excluir_id)
        if a.id_turno.id_bloque.es_nocturno
    }
    noches.add(fecha)

    racha = 1
    d = fecha - timedelta(days=1)
    while d in noches:
        racha += 1
        d -= timedelta(days=1)
    d = fecha + timedelta(days=1)
    while d in noches:
        racha += 1
        d += timedelta(days=1)
    return racha
def validar_competencias(usuario, turno):
    errores = []
    fecha = turno.id_malla.fecha
    if not UsuarioPuesto.objects.filter(id_usuario=usuario, id_puesto=turno.id_puesto).exists():
        errores.append(f'No tiene el puesto requerido: {turno.id_puesto}.')
    maquina = turno.id_maquinaria_req
    if maquina:
        if not UsuarioMaquinaria.objects.filter(
            Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gte=fecha),
            id_usuario=usuario,
            id_maquinaria=maquina,
        ).exists():
            errores.append(f'No está certificado para operar: {maquina.nombre_maquinaria}.')

    licencia_requerida = turno.id_tipo_licencia_req
    if licencia_requerida is None and maquina is not None:
        licencia_requerida = maquina.id_tipo_licencia_requerida
    if licencia_requerida and not UsuarioLicencia.objects.filter(
        id_usuario=usuario,
        id_tipo_licencia=licencia_requerida,
        fecha_vencimiento__gte=fecha,
    ).exists():
        errores.append(f'No tiene licencia vigente: {licencia_requerida.nombre_licencia}.')

    return errores


def validar_asignacion(usuario, turno, excluir_id=None):
    fecha = turno.id_malla.fecha
    bloque = turno.id_bloque

    if usuario.id_rol_id != Roles.TRABAJADOR:
        return ['Solo se pueden asignar usuarios con rol Trabajador.']
    if usuario.estado != 'activo' or not usuario.is_active:
        return ['El trabajador no está activo.']
    contrato = usuario.id_contrato
    if contrato is None:
        return ['El trabajador no tiene contrato asignado.']

    errores = validar_competencias(usuario, turno)
    if errores:
        return errores

    if asignaciones_activas(usuario, fecha, fecha, excluir_id).exists():
        errores.append('Ya tiene un turno asignado para esta fecha.')

    inicio, fin = bloque.intervalo(fecha)
    descanso_minimo = timedelta(hours=settings.HORARIO_DESCANSO_MINIMO_HORAS)
    cercanas = asignaciones_activas(
        usuario, fecha - timedelta(days=1), fecha + timedelta(days=1), excluir_id
    )
    for otra in cercanas:
        ini_o, fin_o = otra.id_turno.id_bloque.intervalo(otra.id_turno.id_malla.fecha)
        separacion = max(ini_o - fin, inicio - fin_o)
        if separacion < descanso_minimo:
            errores.append(
                f'No respeta el descanso mínimo de {settings.HORARIO_DESCANSO_MINIMO_HORAS} h entre turnos.'
            )
            break

    semana = asignaciones_de_la_semana(usuario, fecha, excluir_id)
    horas_semana = sum(a.id_turno.id_bloque.duracion_horas() for a in semana)
    horas_nuevas = horas_semana + bloque.duracion_horas()

    if horas_nuevas > settings.HORARIO_LIMITE_SEMANAL_LEGAL:
        errores.append(
            f'Superaría el límite legal semanal de {settings.HORARIO_LIMITE_SEMANAL_LEGAL} h.'
        )
    elif horas_nuevas > contrato.horas_semanales_pactadas and not contrato.permite_horas_extra:
        errores.append(
            f'Superaría las {contrato.horas_semanales_pactadas} h pactadas y el contrato no permite horas extra.'
        )

    if bloque.es_nocturno:
        if contrato.max_noches_semana is not None:
            noches_semana = sum(1 for a in semana if a.id_turno.id_bloque.es_nocturno)
            if noches_semana + 1 > contrato.max_noches_semana:
                errores.append(
                    f'Su contrato permite máximo {contrato.max_noches_semana} noches a la semana.'
                )

        if contrato.max_noches_consecutivas is not None:
            racha = _largo_racha_nocturna(usuario, fecha, excluir_id)
            if racha > contrato.max_noches_consecutivas:
                errores.append(
                    f'Su contrato permite máximo {contrato.max_noches_consecutivas} noche(s) seguida(s).'
                )

    return errores


def candidatos_para_turno(turno):
    fecha = turno.id_malla.fecha
    usuarios = (
        Usuario.objects
        .filter(
            id_rol_id=Roles.TRABAJADOR,
            estado='activo',
            is_active=True,
            id_contrato__isnull=False,
        )
        .select_related('id_contrato')
    )

    aptos = []
    for usuario in usuarios:
        if not validar_asignacion(usuario, turno):
            aptos.append((horas_de_la_semana(usuario, fecha), usuario))

    aptos.sort(key=lambda par: (par[0], par[1].apellidos, par[1].nombres))
    return aptos