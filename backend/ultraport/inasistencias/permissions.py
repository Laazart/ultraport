from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarios.permissions import PERMISOS_POR_ROL, Permisos


def tiene_permiso(usuario, permiso):
    return permiso in PERMISOS_POR_ROL.get(usuario.id_rol_id, set())


def es_encargado(usuario):
    return tiene_permiso(usuario, Permisos.GESTIONAR_INASISTENCIA)


class PuedeNotificarOConsultar(BasePermission):
    """el trabajador registra y ve sus avisos, el encargado solo los consulta"""
    message = 'Tu rol no tiene acceso a los avisos de inasistencia.'

    def has_permission(self, request, view):
        if tiene_permiso(request.user, Permisos.NOTIFICAR_INASISTENCIA):
            return True
        return request.method in SAFE_METHODS and es_encargado(request.user)
