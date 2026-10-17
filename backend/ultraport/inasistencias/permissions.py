from rest_framework.permissions import BasePermission

ROLES_GESTION = ('Encargado de Planificacion', 'Administrador')


def es_encargado(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    return bool(usuario.id_rol and usuario.id_rol.nombre_rol in ROLES_GESTION)


class EsEncargado(BasePermission):
    message = 'Solo el encargado de planificación puede gestionar los avisos.'

    def has_permission(self, request, view):
        return es_encargado(request.user)
