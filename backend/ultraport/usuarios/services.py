import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import resend
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Value
from django.db.models.functions import Replace, Upper
from django.utils import timezone

from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from auditoria.acciones import Acciones, Entidades
from auditoria.services import registrar
from .historial_password import MENSAJE_PASSWORD_REUTILIZADA, password_reutilizada
from .models import TokenRecuperacion, Usuario, UsuarioLicencia, UsuarioMaquinaria, UsuarioPuesto
from .validar_rut import normalizar_rut

resend.api_key = settings.RESEND_API_KEY


def buscar_usuario_por_identificador(identificador):
    """Devuelve el usuario cuyo correo o RUT coincide, o None.

    El RUT se normaliza (sin puntos, con guion, DV en mayúscula) y se compara
    contra el RUT guardado sin puntos y en mayúsculas, para encontrar también
    registros guardados con otro formato.
    """
    identificador = (identificador or '').strip()
    if not identificador:
        return None
    if '@' in identificador:
        return Usuario.objects.filter(correo__iexact=identificador).first()
    try:
        rut = normalizar_rut(identificador)
    except ValidationError:
        return None
    return (
        Usuario.objects
        .annotate(rut_normalizado=Replace(Upper('rut'), Value('.'), Value('')))
        .filter(rut_normalizado=rut)
        .first()
    )


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def crear_token_recuperacion(usuario):
    TokenRecuperacion.objects.filter(id_usuario=usuario, usado=False).update(usado=True)

    token = secrets.token_urlsafe(32)
    TokenRecuperacion.objects.create(
        id_usuario=usuario,
        token_hash=_hash(token),
        fecha_expiracion=timezone.now() + timedelta(minutes=settings.RECUPERACION_EXPIRA_MINUTOS),
    )
    return token


def construir_enlace_recuperacion(token):
    """URL de la página RestablecerPassword del frontend (ruta /resetear-password, lee ?token=)."""
    return f"{settings.FRONTEND_URL.rstrip('/')}/resetear-password?{urlencode({'token': token})}"


def enviar_correo_recuperacion(usuario, token):
    enlace = construir_enlace_recuperacion(token)
    resend.Emails.send({
        'from': settings.EMAIL_FROM,
        'to': [usuario.correo],
        'subject': 'Recuperar contraseña',
        'html': (
            f'<p>Hola {usuario.nombres},</p>'
            f'<p>Para restablecer tu contraseña, haz clic aquí:</p>'
            f'<p><a href="{enlace}">Restablecer contraseña</a></p>'
            f'<p>El enlace expira en {settings.RECUPERACION_EXPIRA_MINUTOS} minutos. '
            f'Si no lo pediste, ignora este correo.</p>'
        ),
    })


def validar_token(token):
    registro = (
        TokenRecuperacion.objects
        .select_related('id_usuario')
        .filter(token_hash=_hash(token), usado=False, fecha_expiracion__gte=timezone.now())
        .first()
    )
    return registro


# --- Escritura de usuarios (con auditoría) ---
#
# Cada servicio recibe `actor` (obligatorio, keyword) y registra en auditoría
# dentro de su propia transacción: si algo falla, no queda registro. Los
# detalles nunca incluyen contraseñas, hashes ni tokens, ni valores de datos
# personales (solo los nombres de los campos cambiados).

def _validar_password_nueva(usuario, password):
    if password_reutilizada(usuario, password):
        raise DRFValidationError({'password': [MENSAJE_PASSWORD_REUTILIZADA]})


def _tipo_contrato(contrato):
    return contrato.tipo if contrato else None


@transaction.atomic
def crear_usuario(datos, *, actor):
    datos = dict(datos)
    password = datos.pop('password')
    usuario = Usuario(**datos)
    usuario.set_password(password)
    usuario.save()
    registrar(actor, Acciones.USUARIO_CREAR, Entidades.USUARIO, usuario.pk, {
        'rol': usuario.id_rol_id,
        'contrato': _tipo_contrato(usuario.id_contrato),
        'estado': usuario.estado,
    })
    return usuario


@transaction.atomic
def actualizar_usuario(usuario, datos, *, actor):
    datos = dict(datos)
    password = datos.pop('password', None)
    if password:
        _validar_password_nueva(usuario, password)

    antes = {campo: getattr(usuario, campo) for campo in datos}
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    if 'estado' in datos:
        # is_active sigue a estado en ambos sentidos (reactivar/desactivar).
        usuario.is_active = usuario.estado == 'activo'
    if password:
        usuario.set_password(password)
    usuario.save()

    cambiados = {campo for campo in datos if antes[campo] != getattr(usuario, campo)}
    editados = sorted(cambiados - {'estado', 'id_contrato'})
    if editados:
        registrar(actor, Acciones.USUARIO_EDITAR, Entidades.USUARIO, usuario.pk, {'campos': editados})
    if 'estado' in cambiados:
        accion = Acciones.USUARIO_REACTIVAR if usuario.estado == 'activo' else Acciones.USUARIO_DESACTIVAR
        registrar(actor, accion, Entidades.USUARIO, usuario.pk, {'via': 'edicion'})
    if 'id_contrato' in cambiados:
        registrar(actor, Acciones.USUARIO_CONTRATO, Entidades.USUARIO, usuario.pk, {
            'de': _tipo_contrato(antes['id_contrato']), 'a': _tipo_contrato(usuario.id_contrato),
        })
    if password:
        registrar(actor, Acciones.USUARIO_PASSWORD, Entidades.USUARIO, usuario.pk, {'via': 'edicion'})
    return usuario


@transaction.atomic
def desactivar_usuario(usuario, *, actor):
    """Baja lógica. Si ya estaba inactivo no cambia nada ni registra."""
    if usuario.estado == 'inactivo' and not usuario.is_active:
        return usuario
    usuario.estado = 'inactivo'
    usuario.is_active = False
    usuario.save(update_fields=['estado', 'is_active'])
    registrar(actor, Acciones.USUARIO_DESACTIVAR, Entidades.USUARIO, usuario.pk, {'via': 'baja'})
    return usuario


@transaction.atomic
def restablecer_password(registro, password):
    """
    Cambia la contraseña con un token de recuperación válido. El actor es el
    propio usuario. Si la contraseña se rechaza, el token queda sin usar.
    """
    usuario = registro.id_usuario
    _validar_password_nueva(usuario, password)
    usuario.set_password(password)
    usuario.save(update_fields=['password'])  # registra la anterior en el historial
    registro.usado = True
    registro.save(update_fields=['usado'])
    registrar(usuario, Acciones.USUARIO_PASSWORD, Entidades.USUARIO, usuario.pk, {'via': 'restablecer'})
    return usuario


# --- Competencias ---

def esta_vencida(fecha_vencimiento):
    return fecha_vencimiento is not None and fecha_vencimiento < timezone.localdate()


def advertencias_competencias(usuario):
    """Máquinas certificadas sin la licencia vigente que requieren (no bloquea)."""
    licencias = dict(usuario.licencias.values_list('id_tipo_licencia_id', 'fecha_vencimiento'))
    maquinas = [m.id_maquinaria for m in usuario.maquinarias.select_related(
        'id_maquinaria__id_tipo_licencia_requerida')]
    avisos = []
    for maquina in maquinas:
        requerida = maquina.id_tipo_licencia_requerida
        if requerida is None:
            continue
        if requerida.pk not in licencias:
            avisos.append(
                f'{maquina.nombre_maquinaria} requiere la licencia {requerida.nombre_licencia}, '
                'que el trabajador no tiene.')
        elif esta_vencida(licencias[requerida.pk]):
            avisos.append(
                f'{maquina.nombre_maquinaria} requiere la licencia {requerida.nombre_licencia}, '
                'que está vencida.')
    return avisos


def _sincronizar(actuales, entrantes, crear, actualizar, quitar):
    """
    Empareja por clave: actualiza las existentes, crea las nuevas y quita las que
    no vienen. Devuelve {'agregados', 'editados', 'quitados'} con las claves.
    """
    resumen = {'agregados': [], 'editados': [], 'quitados': []}
    for clave in sorted(set(actuales) - set(entrantes)):
        quitar(actuales[clave])
        resumen['quitados'].append(clave)
    for clave, item in entrantes.items():
        if clave in actuales:
            if actualizar(actuales[clave], item):
                resumen['editados'].append(clave)
        else:
            crear(item)
            resumen['agregados'].append(clave)
    return resumen


@transaction.atomic
def guardar_competencias(usuario, datos, *, actor):
    """
    Reemplaza puestos, licencias y maquinaria (solo las listas enviadas) y
    devuelve las advertencias. Registra un resumen de ids si hubo cambios.
    """
    resumen = {}

    if 'puestos' in datos:
        resumen['puestos'] = _sincronizar(
            actuales={p.id_puesto_id: p for p in usuario.puestos.all()},
            entrantes={p.pk: p for p in datos['puestos']},
            crear=lambda puesto: UsuarioPuesto.objects.create(id_usuario=usuario, id_puesto=puesto),
            actualizar=lambda actual, item: False,
            quitar=lambda actual: actual.delete(),
        )

    if 'licencias' in datos:
        def actualizar_licencia(licencia, item):
            nuevos = {'fecha_emision': item['fecha_emision'], 'fecha_vencimiento': item['fecha_vencimiento']}
            if 'especialidades' in item:
                nuevos['especialidades'] = item['especialidades']
            if all(getattr(licencia, c) == v for c, v in nuevos.items()):
                return False
            for campo, valor in nuevos.items():
                setattr(licencia, campo, valor)
            licencia.save()
            return True

        resumen['licencias'] = _sincronizar(
            actuales={l.id_tipo_licencia_id: l for l in usuario.licencias.all()},
            entrantes={l['id_tipo_licencia'].pk: l for l in datos['licencias']},
            crear=lambda item: UsuarioLicencia.objects.create(
                id_usuario=usuario, id_tipo_licencia=item['id_tipo_licencia'],
                especialidades=item.get('especialidades', ''),
                fecha_emision=item['fecha_emision'], fecha_vencimiento=item['fecha_vencimiento']),
            actualizar=actualizar_licencia,
            quitar=lambda actual: actual.delete(),
        )

    if 'maquinarias' in datos:
        def actualizar_certificacion(certificacion, item):
            vencimiento = item.get('fecha_vencimiento')
            if certificacion.fecha_vencimiento == vencimiento:
                return False
            certificacion.fecha_vencimiento = vencimiento
            certificacion.save()
            return True

        resumen['maquinarias'] = _sincronizar(
            actuales={m.id_maquinaria_id: m for m in usuario.maquinarias.all()},
            entrantes={m['id_maquinaria'].pk: m for m in datos['maquinarias']},
            crear=lambda item: UsuarioMaquinaria.objects.create(
                id_usuario=usuario, id_maquinaria=item['id_maquinaria'],
                fecha_vencimiento=item.get('fecha_vencimiento')),
            actualizar=actualizar_certificacion,
            quitar=lambda actual: actual.delete(),
        )

    advertencias = advertencias_competencias(usuario)
    hubo_cambios = any(lista for cambios in resumen.values() for lista in cambios.values())
    if hubo_cambios:
        registrar(actor, Acciones.USUARIO_COMPETENCIAS, Entidades.USUARIO, usuario.pk, {
            **resumen, 'advertencias': len(advertencias),
        })
    return advertencias