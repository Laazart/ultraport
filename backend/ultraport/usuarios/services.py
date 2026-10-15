import hashlib
import secrets
from datetime import timedelta

import resend
from django.conf import settings
from django.utils import timezone

from .models import TokenRecuperacion, Usuario

resend.api_key = settings.RESEND_API_KEY


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


def enviar_correo_recuperacion(usuario, token):
    enlace = f'{settings.FRONTEND_URL}/resetear-password?token={token}'
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