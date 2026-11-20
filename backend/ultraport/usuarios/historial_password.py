"""
Impide reutilizar contraseñas: la actual y las últimas MAX_HISTORIAL_PASSWORD.

El historial guarda solo hashes (nunca texto plano). Se registra desde
Usuario.set_password/save, así que cubre cualquier flujo que cambie la
contraseña; el rechazo lo hacen los flujos de la API y el validador de
AUTH_PASSWORD_VALIDATORS (por ejemplo, manage.py changepassword).
"""
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError

MAX_HISTORIAL_PASSWORD = 5
MENSAJE_PASSWORD_REUTILIZADA = 'No puedes usar una contraseña que ya utilizaste anteriormente.'


def password_reutilizada(usuario, nueva):
    """True si `nueva` coincide con la contraseña actual o con una de las últimas del historial."""
    if usuario.pk is None:
        return False
    # hashers.check_password sin setter: no re-hashea ni guarda el usuario como efecto secundario.
    if usuario.password and check_password(nueva, usuario.password):
        return True
    from .models import HistorialPassword
    anteriores = (
        HistorialPassword.objects
        .filter(id_usuario_id=usuario.pk)
        .order_by('-fecha', '-id_historial')
        .values_list('password_hash', flat=True)[:MAX_HISTORIAL_PASSWORD]
    )
    return any(check_password(nueva, hash_anterior) for hash_anterior in anteriores)


def registrar_password_anterior(usuario, hash_anterior):
    """Guarda el hash reemplazado y deja solo los MAX_HISTORIAL_PASSWORD más recientes."""
    from .models import HistorialPassword
    HistorialPassword.objects.create(id_usuario=usuario, password_hash=hash_anterior)
    historial = HistorialPassword.objects.filter(id_usuario=usuario)
    conservar = list(
        historial.order_by('-fecha', '-id_historial')
        .values_list('id_historial', flat=True)[:MAX_HISTORIAL_PASSWORD]
    )
    historial.exclude(id_historial__in=conservar).delete()


class NoReutilizarPasswordValidator:
    """Validador para AUTH_PASSWORD_VALIDATORS. Solo actúa sobre usuarios ya existentes."""

    def validate(self, password, user=None):
        if user is not None and password_reutilizada(user, password):
            raise ValidationError(MENSAJE_PASSWORD_REUTILIZADA, code='password_reutilizada')

    def get_help_text(self):
        return 'No puedes reutilizar tu contraseña actual ni las últimas cinco.'
