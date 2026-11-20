"""Catálogo de acciones auditadas (valor guardado en BD -> etiqueta legible)."""


class Acciones:
    USUARIO_CREAR = 'usuario.crear'
    USUARIO_EDITAR = 'usuario.editar'
    USUARIO_DESACTIVAR = 'usuario.desactivar'
    USUARIO_REACTIVAR = 'usuario.reactivar'
    USUARIO_CONTRATO = 'usuario.contrato'
    USUARIO_COMPETENCIAS = 'usuario.competencias'
    USUARIO_PASSWORD = 'usuario.password'

    MALLA_INICIAR = 'malla.iniciar'
    MALLA_AUTOCOMPLETAR = 'malla.autocompletar'
    MALLA_PUBLICAR = 'malla.publicar'

    ASIGNACION_ASIGNAR = 'asignacion.asignar'
    ASIGNACION_QUITAR = 'asignacion.quitar'
    ASIGNACION_MOVER = 'asignacion.mover'
    ASIGNACION_REEMPLAZAR = 'asignacion.reemplazar'

    INASISTENCIA_CREAR = 'inasistencia.crear'
    INASISTENCIA_ESTADO = 'inasistencia.estado'


ACCIONES = [
    (Acciones.USUARIO_CREAR, 'Crear usuario'),
    (Acciones.USUARIO_EDITAR, 'Editar usuario'),
    (Acciones.USUARIO_DESACTIVAR, 'Desactivar usuario'),
    (Acciones.USUARIO_REACTIVAR, 'Reactivar usuario'),
    (Acciones.USUARIO_CONTRATO, 'Cambiar contrato'),
    (Acciones.USUARIO_COMPETENCIAS, 'Editar competencias'),
    (Acciones.USUARIO_PASSWORD, 'Cambiar contraseña'),
    (Acciones.MALLA_INICIAR, 'Iniciar malla'),
    (Acciones.MALLA_AUTOCOMPLETAR, 'Autocompletar malla'),
    (Acciones.MALLA_PUBLICAR, 'Publicar malla'),
    (Acciones.ASIGNACION_ASIGNAR, 'Asignar trabajador'),
    (Acciones.ASIGNACION_QUITAR, 'Quitar asignación'),
    (Acciones.ASIGNACION_MOVER, 'Mover asignación'),
    (Acciones.ASIGNACION_REEMPLAZAR, 'Reemplazar trabajador'),
    (Acciones.INASISTENCIA_CREAR, 'Enviar aviso de inasistencia'),
    (Acciones.INASISTENCIA_ESTADO, 'Cambiar estado de inasistencia'),
]


class Entidades:
    USUARIO = 'usuario'
    MALLA = 'malla'
    ASIGNACION = 'asignacion'
    INASISTENCIA = 'inasistencia'


ENTIDADES = [
    (Entidades.USUARIO, 'Usuario'),
    (Entidades.MALLA, 'Malla'),
    (Entidades.ASIGNACION, 'Asignación'),
    (Entidades.INASISTENCIA, 'Inasistencia'),
]
