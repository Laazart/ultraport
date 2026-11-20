from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from horario.models import BloqueTurno, Malla, Turno
from horario.reglas import validar_asignacion
from .models import (
    Contrato, Maquinaria, Puesto, TipoLicencia,
    Usuario, UsuarioLicencia, UsuarioMaquinaria, UsuarioPuesto,
)
from .permissions import Roles
from .serializers import MENSAJE_VENCIMIENTO_ANTERIOR
from .tests import crear_usuario


def _url(usuario):
    return f'/api/usuarios/{usuario.pk}/competencias/'


class CompetenciasTests(APITestCase):
    def setUp(self):
        self.encargado = crear_usuario('encargado@test.cl', '11111111-1', rol=Roles.PLANIFICADOR)
        self.trabajador = crear_usuario('trabajador@test.cl', '22222222-2')
        self.client.force_authenticate(self.encargado)

        self.capataz, _ = Puesto.objects.get_or_create(nombre_puesto='Capataz CT')
        self.operador, _ = Puesto.objects.get_or_create(nombre_puesto='Operador CT')
        self.lic_b = TipoLicencia.objects.create(nombre_licencia='B-CT', descripcion='Clase B')
        self.lic_d = TipoLicencia.objects.create(nombre_licencia='D-CT', descripcion='Clase D')
        self.grua = Maquinaria.objects.create(
            nombre_maquinaria='Grúa CT', especialidad='Izaje', id_tipo_licencia_requerida=self.lic_d)
        self.horquilla = Maquinaria.objects.create(nombre_maquinaria='Horquilla CT', especialidad='Carga')

        self.hoy = timezone.localdate()

    def _put(self, datos, usuario=None):
        return self.client.put(_url(usuario or self.trabajador), datos, format='json')

    def _licencia(self, tipo, emision, vencimiento):
        return {'id_tipo_licencia': tipo.pk, 'fecha_emision': str(emision),
                'fecha_vencimiento': str(vencimiento)}

    # --- Puestos ---

    def test_asignar_y_quitar_puestos(self):
        resp = self._put({'puestos': [self.capataz.pk, self.operador.pk]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            {p['id_puesto'] for p in resp.data['puestos']}, {self.capataz.pk, self.operador.pk})

        resp = self._put({'puestos': [self.operador.pk]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            list(UsuarioPuesto.objects.filter(id_usuario=self.trabajador)
                 .values_list('id_puesto_id', flat=True)),
            [self.operador.pk])

    def test_puesto_repetido_no_duplica(self):
        resp = self._put({'puestos': [self.capataz.pk, self.capataz.pk]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(UsuarioPuesto.objects.filter(id_usuario=self.trabajador).count(), 1)

    # --- Licencias ---

    def test_agregar_editar_y_quitar_licencia(self):
        emision = self.hoy - timedelta(days=30)
        resp = self._put({'licencias': [self._licencia(self.lic_b, emision, self.hoy + timedelta(days=300))]})
        self.assertEqual(resp.status_code, 200)
        original = UsuarioLicencia.objects.get(id_usuario=self.trabajador)

        nuevo_venc = self.hoy + timedelta(days=700)
        resp = self._put({'licencias': [self._licencia(self.lic_b, emision, nuevo_venc)]})
        self.assertEqual(resp.status_code, 200)
        editada = UsuarioLicencia.objects.get(id_usuario=self.trabajador)
        self.assertEqual(editada.pk, original.pk)  # se actualiza, no se recrea
        self.assertEqual(editada.fecha_vencimiento, nuevo_venc)

        resp = self._put({'licencias': []})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(UsuarioLicencia.objects.filter(id_usuario=self.trabajador).exists())

    def test_licencia_vencida_se_marca(self):
        resp = self._put({'licencias': [
            self._licencia(self.lic_b, self.hoy - timedelta(days=800), self.hoy - timedelta(days=1)),
            self._licencia(self.lic_d, self.hoy - timedelta(days=10), self.hoy + timedelta(days=10)),
        ]})
        vencidas = {l['nombre_licencia']: l['vencida'] for l in resp.data['licencias']}
        self.assertEqual(vencidas, {'B-CT': True, 'D-CT': False})

    def test_vencimiento_debe_ser_posterior_a_emision(self):
        for vencimiento in (self.hoy, self.hoy - timedelta(days=1)):
            with self.subTest(vencimiento=vencimiento):
                resp = self._put({'licencias': [self._licencia(self.lic_b, self.hoy, vencimiento)]})
                self.assertEqual(resp.status_code, 400)
                self.assertIn(MENSAJE_VENCIMIENTO_ANTERIOR, str(resp.data))
        self.assertFalse(UsuarioLicencia.objects.filter(id_usuario=self.trabajador).exists())

    def test_endpoint_usuario_licencias_tambien_valida_fechas(self):
        resp = self.client.post('/api/usuario-licencias/', {
            'id_usuario': self.trabajador.pk, 'id_tipo_licencia': self.lic_b.pk,
            'especialidades': '', 'fecha_emision': '2026-05-01', 'fecha_vencimiento': '2026-04-01',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_licencia_repetida_se_rechaza(self):
        lic = self._licencia(self.lic_b, self.hoy, self.hoy + timedelta(days=10))
        resp = self._put({'licencias': [lic, lic]})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('repetida', str(resp.data['licencias']))

    def test_error_no_deja_cambios_a_medias(self):
        resp = self._put({
            'puestos': [self.capataz.pk],
            'licencias': [self._licencia(self.lic_b, self.hoy, self.hoy)],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(UsuarioPuesto.objects.filter(id_usuario=self.trabajador).exists())

    # --- Maquinaria ---

    def test_agregar_editar_y_quitar_maquinaria(self):
        resp = self._put({'maquinarias': [{'id_maquinaria': self.horquilla.pk, 'fecha_vencimiento': None}]})
        self.assertEqual(resp.status_code, 200)
        original = UsuarioMaquinaria.objects.get(id_usuario=self.trabajador)
        self.assertIsNone(original.fecha_vencimiento)

        venc = self.hoy + timedelta(days=90)
        resp = self._put({'maquinarias': [{'id_maquinaria': self.horquilla.pk, 'fecha_vencimiento': str(venc)}]})
        editada = UsuarioMaquinaria.objects.get(id_usuario=self.trabajador)
        self.assertEqual(editada.pk, original.pk)
        self.assertEqual(editada.fecha_vencimiento, venc)

        self._put({'maquinarias': []})
        self.assertFalse(UsuarioMaquinaria.objects.filter(id_usuario=self.trabajador).exists())

    def test_maquina_repetida_se_rechaza(self):
        item = {'id_maquinaria': self.horquilla.pk}
        resp = self._put({'maquinarias': [item, item]})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('repetida', str(resp.data['maquinarias']))

    def test_certificacion_vencida_se_marca(self):
        resp = self._put({'maquinarias': [
            {'id_maquinaria': self.horquilla.pk, 'fecha_vencimiento': str(self.hoy - timedelta(days=1))}]})
        self.assertTrue(resp.data['maquinarias'][0]['vencida'])

    def test_maquina_sin_licencia_requerida_avisa_sin_bloquear(self):
        resp = self._put({'maquinarias': [{'id_maquinaria': self.grua.pk}]})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(UsuarioMaquinaria.objects.filter(id_usuario=self.trabajador).exists())
        self.assertEqual(len(resp.data['advertencias']), 1)
        self.assertIn('D-CT', resp.data['advertencias'][0])

    def test_maquina_con_licencia_vencida_avisa(self):
        resp = self._put({
            'licencias': [self._licencia(self.lic_d, self.hoy - timedelta(days=800), self.hoy - timedelta(days=1))],
            'maquinarias': [{'id_maquinaria': self.grua.pk}],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('vencida', resp.data['advertencias'][0])

    def test_maquina_con_licencia_vigente_no_avisa(self):
        resp = self._put({
            'licencias': [self._licencia(self.lic_d, self.hoy, self.hoy + timedelta(days=10))],
            'maquinarias': [{'id_maquinaria': self.grua.pk}, {'id_maquinaria': self.horquilla.pk}],
        })
        self.assertEqual(resp.data['advertencias'], [])

    # --- Contrato ---

    def test_contrato_se_edita_y_aparece_en_competencias(self):
        contrato = Contrato.objects.create(
            tipo='cppt', modalidad='4x3', turno_habitual='rotativo',
            horas_semanales_pactadas=42, fecha_inicio=date(2026, 1, 1))
        resp = self.client.patch(
            f'/api/usuarios/{self.trabajador.pk}/', {'id_contrato': contrato.pk}, format='json')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(_url(self.trabajador))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['contrato']['id_contrato'], contrato.pk)
        self.assertEqual(resp.data['contrato']['tipo_display'], 'CPPT')

    # --- Permisos ---

    def test_permisos(self):
        admin = crear_usuario('admin@test.cl', '33333333-3', rol=Roles.ADMINISTRADOR)
        for usuario, esperado in ((self.encargado, 200), (admin, 200), (self.trabajador, 403)):
            with self.subTest(rol=usuario.id_rol_id):
                self.client.force_authenticate(usuario)
                self.assertEqual(self.client.get(_url(self.trabajador)).status_code, esperado)
                self.assertEqual(self._put({'puestos': [self.capataz.pk]}).status_code, esperado)

    def test_trabajador_no_puede_editar_sus_propias_competencias(self):
        self.client.force_authenticate(self.trabajador)
        resp = self._put({'licencias': []})
        self.assertEqual(resp.status_code, 403)

    def test_sin_autenticar(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(_url(self.trabajador)).status_code, 401)


class QuitarLicenciaAfectaAsignacionTests(APITestCase):
    def test_tras_quitar_licencia_ya_no_es_apto(self):
        encargado = crear_usuario('enc@test.cl', '11111111-1', rol=Roles.PLANIFICADOR)
        contrato = Contrato.objects.create(
            tipo='eventual', turno_habitual='rotativo', horas_semanales_pactadas=45,
            permite_horas_extra=True, fecha_inicio=date(2026, 1, 1))
        trabajador = crear_usuario('trab@test.cl', '22222222-2', id_contrato=contrato)
        puesto, _ = Puesto.objects.get_or_create(nombre_puesto='Operador Grúa CT')
        licencia = TipoLicencia.objects.create(nombre_licencia='D-QL', descripcion='Clase D')

        fecha = timezone.localdate() + timedelta(days=7)
        turno = Turno.objects.create(
            id_malla=Malla.objects.get_or_create(fecha=fecha)[0],
            id_bloque=BloqueTurno.objects.get(orden_secuencia=1),
            id_puesto=puesto, cupos=1, id_tipo_licencia_req=licencia,
        )

        self.client.force_authenticate(encargado)
        resp = self.client.put(_url(trabajador), {
            'puestos': [puesto.pk],
            'licencias': [{'id_tipo_licencia': licencia.pk,
                           'fecha_emision': str(fecha - timedelta(days=100)),
                           'fecha_vencimiento': str(fecha + timedelta(days=100))}],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        trabajador = Usuario.objects.get(pk=trabajador.pk)
        self.assertEqual(validar_asignacion(trabajador, turno), [])

        resp = self.client.put(_url(trabajador), {'licencias': []}, format='json')
        self.assertEqual(resp.status_code, 200)
        errores = validar_asignacion(Usuario.objects.get(pk=trabajador.pk), turno)
        self.assertEqual(errores, ['No tiene licencia vigente: D-QL.'])
