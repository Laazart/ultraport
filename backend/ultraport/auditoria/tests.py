import json
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from horario.models import Asignacion, Malla, NotificacionInasistencia
from horario.tests_malla import _BaseMalla, _rut_valido
from usuarios.models import Contrato, Puesto, Rol, TipoLicencia, Usuario
from usuarios.permissions import Roles
from usuarios.serializers import UsuarioSerializer
from usuarios.services import crear_token_recuperacion
from usuarios.tests import PASSWORD, crear_usuario

from . import services as auditoria_services
from .acciones import Acciones, Entidades
from .models import RegistroAuditoria
from .services import registrar, sanear_detalle

MOTIVO_SENSIBLE = 'Diagnóstico: hernia lumbar L4-L5'


def _texto_detalles():
    return json.dumps(list(RegistroAuditoria.objects.values_list('detalle', flat=True)), ensure_ascii=False)


class RegistrarTests(SimpleTestCase):
    def test_fuera_de_una_transaccion_falla(self):
        with self.assertRaisesMessage(RuntimeError, 'transacción'):
            registrar(None, Acciones.MALLA_PUBLICAR, Entidades.MALLA, 1, {})

    def test_sanea_claves_prohibidas_en_cualquier_nivel(self):
        detalle = sanear_detalle({
            'password': 'x', 'Password_Hash': 'pbkdf2$...', 'token': 't', 'motivo': MOTIVO_SENSIBLE,
            'url_adjunto': 'a.pdf', 'campos': ['correo'],
            'anidado': {'new_password1': 'y', 'fecha': timezone.localdate(), 'lista': [{'refresh': 'r', 'ok': 1}]},
        })
        self.assertEqual(detalle, {
            'campos': ['correo'],
            'anidado': {'fecha': timezone.localdate().isoformat(), 'lista': [{'ok': 1}]},
        })

    def test_detalle_demasiado_grande_se_trunca(self):
        detalle = sanear_detalle({'texto': 'x' * 5000, 'otro': 1})
        self.assertEqual(detalle, {'truncado': True, 'claves': ['otro', 'texto']})


class _BaseAuditoria(_BaseMalla):
    def _preparar_api(self):
        self._preparar()
        self.encargado = Usuario.objects.create_user(
            f'enc-{_rut_valido()}@test.cl', _rut_valido(), 'Ana', 'Planificadora', 'clave-segura-123',
            id_rol=Rol.objects.get(pk=Roles.PLANIFICADOR),
        )
        self.client.force_authenticate(self.encargado)
        self.futura = timezone.localdate() + timedelta(days=40)

    def _registros(self, accion=None):
        qs = RegistroAuditoria.objects.all()
        return qs.filter(accion=accion) if accion else qs

    def assertRegistro(self, accion, entidad, id_entidad, actor=None):
        registros = self._registros(accion)
        self.assertEqual(registros.count(), 1, f'{accion}: {list(registros.values())}')
        registro = registros.get()
        self.assertEqual(registro.entidad, entidad)
        self.assertEqual(registro.id_entidad, id_entidad)
        self.assertEqual(registro.actor, actor or self.encargado)
        return registro


class AuditoriaMallaYAsignacionesTests(_BaseAuditoria, APITestCase):
    def setUp(self):
        self._preparar_api()

    # --- Malla ---

    def test_iniciar_con_plantilla(self):
        resp = self.client.post('/api/mallas/iniciar-plantilla/', {'fecha': self.futura.isoformat()}, format='json')
        self.assertEqual(resp.status_code, 201)
        registro = self.assertRegistro(Acciones.MALLA_INICIAR, Entidades.MALLA, resp.data['id_malla'])
        self.assertTrue(registro.detalle['plantilla'])
        self.assertEqual(registro.detalle['fecha'], self.futura.isoformat())
        self.assertGreater(registro.detalle['turnos'], 0)

    def test_iniciar_manual(self):
        resp = self.client.post('/api/mallas/iniciar/', {
            'fecha': self.futura.isoformat(),
            'requerimientos': [{'id_bloque': self.primero.pk, 'id_puesto': self.puesto.pk, 'cupos': 2}],
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        registro = self.assertRegistro(Acciones.MALLA_INICIAR, Entidades.MALLA, resp.data['id_malla'])
        self.assertEqual(registro.detalle, {'fecha': self.futura.isoformat(), 'turnos': 1, 'plantilla': False})

    def test_iniciar_fallido_no_registra(self):
        self._malla(self.futura)
        resp = self.client.post('/api/mallas/iniciar/', {
            'fecha': self.futura.isoformat(),
            'requerimientos': [{'id_bloque': self.primero.pk, 'id_puesto': self.puesto.pk, 'cupos': 2}],
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_autocompletar_deja_un_solo_registro_con_el_conteo(self):
        malla = self._malla(self.futura)
        self._turno(malla, self.primero, cupos=2)
        self._trabajador()
        self._trabajador()
        resp = self.client.post(f'/api/mallas/{malla.pk}/autocompletar/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['asignados'], 2)
        registro = self.assertRegistro(Acciones.MALLA_AUTOCOMPLETAR, Entidades.MALLA, malla.pk)
        self.assertEqual(registro.detalle['asignados'], 2)
        self.assertFalse(self._registros(Acciones.ASIGNACION_ASIGNAR).exists())

    def test_publicar(self):
        malla = self._malla(self.futura)
        resp = self.client.post(f'/api/mallas/{malla.pk}/publicar/')
        self.assertEqual(resp.status_code, 200)
        self.assertRegistro(Acciones.MALLA_PUBLICAR, Entidades.MALLA, malla.pk)

    def test_publicar_dos_veces_no_registra_la_segunda(self):
        malla = self._malla(self.futura, publicada=True)
        resp = self.client.post(f'/api/mallas/{malla.pk}/publicar/')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    # --- Asignaciones ---

    def test_asignar(self):
        turno = self._turno(self._malla(self.futura), self.primero)
        trabajador = self._trabajador()
        resp = self.client.post('/api/asignaciones/', {'id_turno': turno.pk, 'id_usuario': trabajador.pk}, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        registro = self.assertRegistro(Acciones.ASIGNACION_ASIGNAR, Entidades.ASIGNACION, resp.data['id_asignacion'])
        self.assertEqual(registro.detalle, {'usuario': trabajador.pk, 'turno': turno.pk, 'malla': turno.id_malla_id})

    def test_asignar_invalido_no_registra(self):
        turno = self._turno(self._malla(self.futura), self.primero)
        sin_puesto = self._trabajador(con_puesto=False)
        resp = self.client.post('/api/asignaciones/', {'id_turno': turno.pk, 'id_usuario': sin_puesto.pk}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_quitar_en_borrador_y_en_publicada(self):
        for publicada, modo in ((False, 'eliminada'), (True, 'reemplazada')):
            with self.subTest(publicada=publicada):
                RegistroAuditoria.objects.all().delete()
                fecha = self.futura + timedelta(days=10 if publicada else 0)
                turno = self._turno(self._malla(fecha, publicada=publicada), self.primero)
                asignacion = self._asignacion(turno, self._trabajador())
                resp = self.client.delete(f'/api/asignaciones/{asignacion.pk}/')
                self.assertEqual(resp.status_code, 204)
                registro = self.assertRegistro(Acciones.ASIGNACION_QUITAR, Entidades.ASIGNACION, asignacion.pk)
                self.assertEqual(registro.detalle['modo'], modo)

    def test_mover(self):
        malla = self._malla(self.futura)
        origen, destino = self._turno(malla, self.primero), self._turno(malla, self.segundo)
        asignacion = self._asignacion(origen, self._trabajador())
        resp = self.client.post(f'/api/asignaciones/{asignacion.pk}/mover/', {'id_turno': destino.pk}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        registro = self.assertRegistro(Acciones.ASIGNACION_MOVER, Entidades.ASIGNACION, asignacion.pk)
        self.assertEqual(registro.detalle['turno_origen'], origen.pk)
        self.assertEqual(registro.detalle['turno_destino'], destino.pk)

    def test_mover_a_otra_malla_no_registra(self):
        origen = self._turno(self._malla(self.futura), self.primero)
        otra = self._turno(self._malla(self.futura + timedelta(days=1)), self.primero)
        asignacion = self._asignacion(origen, self._trabajador())
        resp = self.client.post(f'/api/asignaciones/{asignacion.pk}/mover/', {'id_turno': otra.pk}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_reemplazar_deja_un_solo_registro(self):
        turno = self._turno(self._malla(self.futura), self.primero)
        anterior, nuevo = self._trabajador(), self._trabajador()
        asignacion = self._asignacion(turno, anterior)
        resp = self.client.post(f'/api/asignaciones/{asignacion.pk}/reemplazar/', {'id_usuario': nuevo.pk}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        registro = self.assertRegistro(Acciones.ASIGNACION_REEMPLAZAR, Entidades.ASIGNACION, resp.data['id_asignacion'])
        self.assertEqual(registro.detalle['usuario_anterior'], anterior.pk)
        self.assertEqual(registro.detalle['usuario_nuevo'], nuevo.pk)
        self.assertEqual(self._registros().count(), 1)

    # --- Atomicidad ---

    def test_si_la_accion_falla_despues_de_registrar_no_queda_nada(self):
        turno = self._turno(self._malla(self.futura), self.primero)
        trabajador = self._trabajador()
        registrar_real = auditoria_services.registrar

        def registrar_y_fallar(*args, **kwargs):
            registrar_real(*args, **kwargs)
            raise RuntimeError('falla simulada después de registrar')

        with mock.patch('horario.services.registrar', side_effect=registrar_y_fallar):
            with self.assertRaisesMessage(RuntimeError, 'falla simulada'):
                self.client.post('/api/asignaciones/', {'id_turno': turno.pk, 'id_usuario': trabajador.pk}, format='json')
        self.assertFalse(self._registros().exists())
        self.assertFalse(Asignacion.objects.filter(id_turno=turno).exists())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='auditoria-tests-'))
class AuditoriaInasistenciasTests(_BaseAuditoria, APITestCase):
    @classmethod
    def tearDownClass(cls):
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self._preparar_api()
        self.trabajador = self._trabajador()

    def _enviar_aviso(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.post('/api/inasistencias/mis-avisos/', {
            'motivo': MOTIVO_SENSIBLE,
            'fecha_inicio': self.futura.isoformat(),
            'fecha_fin': (self.futura + timedelta(days=2)).isoformat(),
            'url_adjunto': SimpleUploadedFile('licencia.pdf', b'%PDF-1.4', content_type='application/pdf'),
        }, format='multipart')
        self.client.force_authenticate(self.encargado)
        return resp

    def test_crear_aviso_registra_sin_motivo_ni_adjunto(self):
        resp = self._enviar_aviso()
        self.assertEqual(resp.status_code, 201, resp.data)
        registro = self.assertRegistro(
            Acciones.INASISTENCIA_CREAR, Entidades.INASISTENCIA, resp.data['id_notificacion'], actor=self.trabajador)
        self.assertEqual(registro.detalle, {
            'trabajador': self.trabajador.pk,
            'fecha_inicio': self.futura.isoformat(),
            'fecha_fin': (self.futura + timedelta(days=2)).isoformat(),
        })

    def test_aviso_invalido_no_registra(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.post('/api/inasistencias/mis-avisos/', {
            'motivo': MOTIVO_SENSIBLE, 'fecha_inicio': self.futura.isoformat(),
        }, format='multipart')  # sin adjunto
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_cambio_de_estado(self):
        aviso = NotificacionInasistencia.objects.get(pk=self._enviar_aviso().data['id_notificacion'])
        resp = self.client.patch(f'/api/inasistencias/{aviso.pk}/estado/', {'estado': 'aprobado'}, format='json')
        self.assertEqual(resp.status_code, 200)
        registro = self.assertRegistro(Acciones.INASISTENCIA_ESTADO, Entidades.INASISTENCIA, aviso.pk)
        self.assertEqual(registro.detalle, {'trabajador': self.trabajador.pk, 'de': 'pendiente', 'a': 'aprobado'})

    def test_estado_invalido_no_registra(self):
        aviso = NotificacionInasistencia.objects.get(pk=self._enviar_aviso().data['id_notificacion'])
        antes = self._registros().count()
        resp = self.client.patch(f'/api/inasistencias/{aviso.pk}/estado/', {'estado': 'otro'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self._registros().count(), antes)

    def test_ningun_registro_contiene_el_motivo_ni_el_archivo(self):
        aviso = NotificacionInasistencia.objects.get(pk=self._enviar_aviso().data['id_notificacion'])
        self.client.patch(f'/api/inasistencias/{aviso.pk}/estado/', {'estado': 'rechazado'}, format='json')
        texto = _texto_detalles()
        self.assertEqual(self._registros().count(), 2)
        self.assertNotIn('hernia', texto)
        self.assertNotIn(MOTIVO_SENSIBLE, texto)
        self.assertNotIn('licencia', texto)
        self.assertNotIn('motivo', texto)


# --- Usuarios ---

NUEVA_PASSWORD = 'Muelle-Sur-99x'


class AuditoriaUsuariosTests(APITestCase):
    def setUp(self):
        self.encargado = crear_usuario('enc@test.cl', '11111111-1', rol=Roles.PLANIFICADOR)
        self.trabajador = crear_usuario('trab@test.cl', '22222222-2')
        self.client.force_authenticate(self.encargado)
        self.url = f'/api/usuarios/{self.trabajador.pk}/'

    def _registros(self, accion=None):
        qs = RegistroAuditoria.objects.all()
        return qs.filter(accion=accion) if accion else qs

    def assertRegistro(self, accion, id_entidad, actor=None):
        registros = self._registros(accion)
        self.assertEqual(registros.count(), 1, f'{accion}: {list(registros.values())}')
        registro = registros.get()
        self.assertEqual(registro.entidad, Entidades.USUARIO)
        self.assertEqual(registro.id_entidad, id_entidad)
        self.assertEqual(registro.actor, actor or self.encargado)
        return registro

    # --- Crear / editar ---

    def test_crear(self):
        resp = self.client.post('/api/usuarios/', {
            'rut': '12.345.678-5', 'nombres': 'Ana', 'apellidos': 'Soto', 'correo': 'ana@test.cl',
            'telefono': '912345678', 'id_rol': Roles.TRABAJADOR, 'password': PASSWORD,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        registro = self.assertRegistro(Acciones.USUARIO_CREAR, resp.data['id_usuario'])
        self.assertEqual(registro.detalle, {'rol': Roles.TRABAJADOR, 'contrato': None, 'estado': 'activo'})
        self.assertNotIn('password', resp.data)

    def test_crear_invalido_no_registra(self):
        resp = self.client.post('/api/usuarios/', {
            'rut': '12.345.678-9', 'nombres': 'Ana', 'apellidos': 'Soto', 'correo': 'ana@test.cl',
            'telefono': '912345678', 'id_rol': Roles.TRABAJADOR, 'password': PASSWORD,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_editar_registra_solo_nombres_de_campos(self):
        resp = self.client.patch(self.url, {'nombres': 'Pedro', 'telefono': '987654321'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        registro = self.assertRegistro(Acciones.USUARIO_EDITAR, self.trabajador.pk)
        self.assertEqual(registro.detalle, {'campos': ['nombres', 'telefono']})
        self.assertNotIn('Pedro', _texto_detalles())
        self.assertNotIn('987654321', _texto_detalles())
        self.assertEqual(self._registros().count(), 1)

    def test_editar_sin_cambios_no_registra(self):
        resp = self.client.patch(self.url, {'nombres': self.trabajador.nombres}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self._registros().exists())

    # --- Desactivar / reactivar ---

    def test_desactivar_por_baja(self):
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        registro = self.assertRegistro(Acciones.USUARIO_DESACTIVAR, self.trabajador.pk)
        self.assertEqual(registro.detalle, {'via': 'baja'})
        # Una segunda baja no cambia nada y no registra.
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(self._registros().count(), 1)

    def test_desactivar_y_reactivar_por_edicion(self):
        self.client.patch(self.url, {'estado': 'inactivo'}, format='json')
        self.assertRegistro(Acciones.USUARIO_DESACTIVAR, self.trabajador.pk)
        self.client.patch(self.url, {'estado': 'activo'}, format='json')
        registro = self.assertRegistro(Acciones.USUARIO_REACTIVAR, self.trabajador.pk)
        self.assertEqual(registro.detalle, {'via': 'edicion'})
        self.assertFalse(self._registros(Acciones.USUARIO_EDITAR).exists())

    # --- Contrato ---

    def test_cambio_de_contrato(self):
        cppt = Contrato.objects.get(tipo='cppt')
        self.client.patch(self.url, {'id_contrato': cppt.pk}, format='json')
        registro = self.assertRegistro(Acciones.USUARIO_CONTRATO, self.trabajador.pk)
        self.assertEqual(registro.detalle, {'de': None, 'a': 'cppt'})

        eventual = Contrato.objects.get(tipo='eventual')
        self.client.patch(self.url, {'id_contrato': eventual.pk}, format='json')
        ultimo = self._registros(Acciones.USUARIO_CONTRATO).first()
        self.assertEqual(ultimo.detalle, {'de': 'cppt', 'a': 'eventual'})

    # --- Contraseña ---

    def test_password_por_edicion_registra_solo_el_hecho(self):
        resp = self.client.patch(self.url, {'password': NUEVA_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        registro = self.assertRegistro(Acciones.USUARIO_PASSWORD, self.trabajador.pk)
        self.assertEqual(registro.detalle, {'via': 'edicion'})
        self.assertFalse(self._registros(Acciones.USUARIO_EDITAR).exists())

    def test_password_reutilizada_no_registra(self):
        resp = self.client.patch(self.url, {'password': PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_restablecer_el_actor_es_el_propio_usuario(self):
        self.client.force_authenticate(None)
        token = crear_token_recuperacion(self.trabajador)
        resp = self.client.post('/api/restablecer-password/', {'token': token, 'password': NUEVA_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        registro = self.assertRegistro(Acciones.USUARIO_PASSWORD, self.trabajador.pk, actor=self.trabajador)
        self.assertEqual(registro.detalle, {'via': 'restablecer'})

    def test_restablecer_con_password_reutilizada_no_registra(self):
        self.client.force_authenticate(None)
        token = crear_token_recuperacion(self.trabajador)
        resp = self.client.post('/api/restablecer-password/', {'token': token, 'password': PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    def test_ningun_registro_contiene_passwords_hashes_ni_tokens(self):
        self.client.patch(self.url, {'password': NUEVA_PASSWORD}, format='json')
        self.client.force_authenticate(None)
        token = crear_token_recuperacion(self.trabajador)
        self.client.post('/api/restablecer-password/', {'token': token, 'password': 'Muelle-Este-77x'}, format='json')
        self.trabajador.refresh_from_db()

        self.assertEqual(self._registros(Acciones.USUARIO_PASSWORD).count(), 2)
        texto = _texto_detalles()
        for sensible in (PASSWORD, NUEVA_PASSWORD, 'Muelle-Este-77x', token, self.trabajador.password, 'pbkdf2'):
            self.assertNotIn(sensible, texto)

    # --- Competencias ---

    def _put_competencias(self, datos):
        return self.client.put(f'{self.url}competencias/', datos, format='json')

    def test_competencias_registra_resumen_y_no_repite_sin_cambios(self):
        puesto = Puesto.objects.create(nombre_puesto='Puesto auditoría')
        tipo = TipoLicencia.objects.create(nombre_licencia='Z-AUD', descripcion='Prueba')
        hoy = timezone.localdate()
        datos = {
            'puestos': [puesto.pk],
            'licencias': [{'id_tipo_licencia': tipo.pk, 'fecha_emision': str(hoy),
                           'fecha_vencimiento': str(hoy + timedelta(days=30))}],
        }
        self.assertEqual(self._put_competencias(datos).status_code, 200)
        registro = self.assertRegistro(Acciones.USUARIO_COMPETENCIAS, self.trabajador.pk)
        self.assertEqual(registro.detalle['puestos']['agregados'], [puesto.pk])
        self.assertEqual(registro.detalle['licencias']['agregados'], [tipo.pk])
        self.assertEqual(registro.detalle['advertencias'], 0)

        # Mismo contenido: no hay cambios, no hay registro nuevo.
        self.assertEqual(self._put_competencias(datos).status_code, 200)
        self.assertEqual(self._registros().count(), 1)

        # Quitar todo queda como 'quitados'.
        self._put_competencias({'puestos': [], 'licencias': []})
        ultimo = self._registros(Acciones.USUARIO_COMPETENCIAS).first()
        self.assertEqual(ultimo.detalle['puestos']['quitados'], [puesto.pk])
        self.assertEqual(ultimo.detalle['licencias']['quitados'], [tipo.pk])

    def test_competencias_invalidas_no_registran(self):
        tipo = TipoLicencia.objects.create(nombre_licencia='Z-AUD2', descripcion='Prueba')
        hoy = timezone.localdate()
        resp = self._put_competencias({'licencias': [
            {'id_tipo_licencia': tipo.pk, 'fecha_emision': str(hoy), 'fecha_vencimiento': str(hoy)}]})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(self._registros().exists())

    # --- El serializer no guarda por su cuenta ---

    def test_serializer_no_guarda_sin_el_servicio(self):
        serializer = UsuarioSerializer(self.trabajador, data={'nombres': 'X'}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(NotImplementedError):
            serializer.save()
