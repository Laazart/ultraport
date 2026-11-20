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
from usuarios.models import Rol, Usuario
from usuarios.permissions import Roles

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
