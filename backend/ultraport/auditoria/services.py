"""
Registro de auditoría.

Los servicios de cada app llaman a registrar() dentro de su propia
transacción, después de hacer la acción: si la acción falla, la transacción
se revierte y el registro desaparece con ella.
"""
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection

from .acciones import ACCIONES, ENTIDADES
from .models import RegistroAuditoria

# Nunca se guardan: contraseñas, hashes, tokens ni el motivo/adjunto de una
# inasistencia (puede contener datos de salud). Se comparan sin mayúsculas.
CLAVES_PROHIBIDAS = frozenset({
    'password', 'password1', 'password2', 'new_password1', 'new_password2',
    'password_hash', 'hash', 'token', 'token_hash', 'refresh', 'access',
    'motivo', 'url_adjunto', 'adjunto',
})
MAX_DETALLE_CARACTERES = 2048

_ACCIONES_VALIDAS = {valor for valor, _ in ACCIONES}
_ENTIDADES_VALIDAS = {valor for valor, _ in ENTIDADES}


def _sanear(valor):
    if isinstance(valor, dict):
        return {
            str(k): _sanear(v) for k, v in valor.items()
            if str(k).lower() not in CLAVES_PROHIBIDAS
        }
    if isinstance(valor, (list, tuple, set)):
        return [_sanear(v) for v in valor]
    return valor


def sanear_detalle(detalle):
    """Quita claves prohibidas, normaliza a JSON plano y acota el tamaño."""
    limpio = json.loads(json.dumps(_sanear(detalle or {}), cls=DjangoJSONEncoder))
    if len(json.dumps(limpio)) > MAX_DETALLE_CARACTERES:
        return {'truncado': True, 'claves': sorted(limpio)[:20] if isinstance(limpio, dict) else []}
    return limpio


def registrar(actor, accion, entidad, id_entidad=None, detalle=None):
    """
    Deja constancia de una acción. Debe llamarse dentro de la transacción de
    la acción (transaction.atomic), para que ambas se confirmen o se reviertan juntas.
    """
    if not connection.in_atomic_block:
        raise RuntimeError('registrar() debe llamarse dentro de la transacción de la acción auditada.')
    if accion not in _ACCIONES_VALIDAS:
        raise ValueError(f'Acción de auditoría desconocida: {accion}')
    if entidad not in _ENTIDADES_VALIDAS:
        raise ValueError(f'Entidad de auditoría desconocida: {entidad}')
    return RegistroAuditoria.objects.create(
        actor=actor if getattr(actor, 'pk', None) else None,
        accion=accion,
        entidad=entidad,
        id_entidad=id_entidad,
        detalle=sanear_detalle(detalle),
    )
