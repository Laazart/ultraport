from rest_framework.permissions import BasePermission
class Roles:
    ADMINISTRADOR = 1
    PLANIFICADOR = 2
    TRABAJADOR = 3

class Permisos:
    USUARIOS_GESTIONAR = 'usuarios.gestionar'
    NOTIFICAR_INASISTENCIA = 'notificar.inasistencia'
    GESTIONAR_INASISTENCIA = 'gestionar.inasistencia'
    PLANIFICAR_TURNOS = 'horario.planificar'


PERMISOS_POR_ROL = {
    Roles.ADMINISTRADOR: {
        Permisos.USUARIOS_GESTIONAR,
        Permisos.GESTIONAR_INASISTENCIA,
    },
    Roles.PLANIFICADOR: {
        Permisos.USUARIOS_GESTIONAR,
        Permisos.GESTIONAR_INASISTENCIA,
        Permisos.PLANIFICAR_TURNOS,

    },
    Roles.TRABAJADOR: {
        Permisos.NOTIFICAR_INASISTENCIA,
    },
}

class TienePermiso(BasePermission):
    message = 'No tienes permiso para realizar esta acción.'
    def has_permission(self, request, view):
        permiso = getattr(view, 'permiso_requerido', None)
        if permiso is None:
            return False
        permisos_del_rol = PERMISOS_POR_ROL.get(request.user.id_rol_id, set())
        return permiso in permisos_del_rol

class EsPropietarioDelRecurso(BasePermission):
    message = 'Solo puedes acceder a tus propios registros.'
    def has_object_permission(self, request, view, obj):
        return obj.id_usuario_id == request.user.id_usuario