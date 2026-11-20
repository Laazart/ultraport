from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APITestCase

from .models import Contrato, Usuario
from .permissions import Roles
from .tests import crear_usuario

ANTES = ('usuarios', '0008_auto_20261027_1638')
DESPUES = ('usuarios', '0010_contrato_tipo_unico')
CAMPOS_COPIADOS = [
    'tipo', 'modalidad', 'turno_habitual', 'horas_semanales_pactadas', 'permite_horas_extra',
    'max_noches_consecutivas', 'max_noches_semana', 'fecha_inicio', 'fecha_termino',
]


def _migrar(destino):
    """Migra usuarios a `destino` y devuelve el registro de modelos de ese estado."""
    executor = MigrationExecutor(connection)
    executor.migrate([destino])
    executor.loader.build_graph()
    return executor.loader.project_state([destino]).apps


class FusionContratosMigracionTests(TransactionTestCase):
    """0009 fusiona duplicados idénticos y 0010 agrega la restricción única."""

    # Restaura los datos sembrados por migraciones (roles, contratos, bloques)
    # que el vaciado de TransactionTestCase borraría.
    serialized_rollback = True

    def tearDown(self):
        # Pase lo que pase, la base debe quedar en la última migración.
        _migrar(DESPUES)

    def _usuario(self, apps, n, contrato_id):
        Usuario = apps.get_model('usuarios', 'Usuario')
        return Usuario.objects.create(
            rut=f'{90000000 + n}-0', nombres='Prueba', apellidos=f'Migración {n}',
            correo=f'migracion{n}@test.cl', password='x', id_contrato_id=contrato_id,
        )

    def test_deja_tres_contratos_y_ningun_usuario_pierde_el_suyo(self):
        apps = _migrar(ANTES)
        Contrato_h = apps.get_model('usuarios', 'Contrato')
        originales = list(Contrato_h.objects.order_by('id_contrato').values(*CAMPOS_COPIADOS))
        self.assertEqual(len(originales), 3)

        tipo_esperado = {}
        n = 0
        for valores in originales:
            original = Contrato_h.objects.get(tipo=valores['tipo'], id_contrato__lte=3)
            ids = [original.pk] + [Contrato_h.objects.create(**valores).pk for _ in range(2)]
            for contrato_id in ids:
                n += 1
                tipo_esperado[self._usuario(apps, n, contrato_id).correo] = valores['tipo']
        self.assertEqual(Contrato_h.objects.count(), 9)

        _migrar(DESPUES)

        self.assertEqual(Contrato.objects.count(), 3)
        self.assertEqual(sorted(Contrato.objects.values_list('tipo', flat=True)),
                         ['bono_turno', 'cppt', 'eventual'])
        # Se conservan los de menor id (los sembrados).
        self.assertEqual(sorted(Contrato.objects.values_list('pk', flat=True)), [1, 2, 3])
        for correo, tipo in tipo_esperado.items():
            usuario = Usuario.objects.select_related('id_contrato').get(correo=correo)
            self.assertIsNotNone(usuario.id_contrato, correo)
            self.assertEqual(usuario.id_contrato.tipo, tipo, correo)

    def test_aborta_si_hay_contratos_del_mismo_tipo_con_valores_distintos(self):
        apps = _migrar(ANTES)
        Contrato_h = apps.get_model('usuarios', 'Contrato')
        valores = Contrato_h.objects.filter(tipo='cppt').values(*CAMPOS_COPIADOS).first()
        distinto = Contrato_h.objects.create(**{**valores, 'horas_semanales_pactadas': 45})
        usuario = self._usuario(apps, 1, distinto.pk)

        with self.assertRaisesMessage(RuntimeError, 'cppt'):
            _migrar(DESPUES)

        # No se borró ni se reasignó nada: la migración se revirtió completa.
        self.assertTrue(Contrato_h.objects.filter(pk=distinto.pk).exists())
        apps.get_model('usuarios', 'Usuario').objects.filter(pk=usuario.pk).delete()
        Contrato_h.objects.filter(pk=distinto.pk).delete()


class ContratoTipoUnicoTests(TestCase):
    def test_no_se_puede_crear_un_segundo_contrato_del_mismo_tipo(self):
        existente = Contrato.objects.get(tipo='cppt')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Contrato.objects.create(
                tipo='cppt', turno_habitual=existente.turno_habitual,
                horas_semanales_pactadas=existente.horas_semanales_pactadas,
                fecha_inicio=existente.fecha_inicio,
            )
        self.assertEqual(Contrato.objects.filter(tipo='cppt').count(), 1)


class ContratoApiSoloLecturaTests(APITestCase):
    URL = '/api/contratos/'

    def setUp(self):
        self.encargado = crear_usuario('enc@test.cl', '11111111-1', rol=Roles.PLANIFICADOR)
        self.client.force_authenticate(self.encargado)
        self.contrato = Contrato.objects.get(tipo='bono_turno')

    def test_get_lista_y_detalle(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sorted(c['tipo'] for c in resp.data), ['bono_turno', 'cppt', 'eventual'])
        resp = self.client.get(f'{self.URL}{self.contrato.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['tipo'], 'bono_turno')

    def test_rechaza_escrituras(self):
        datos = {'tipo': 'bono_turno', 'turno_habitual': 'rotativo',
                 'horas_semanales_pactadas': 10, 'fecha_inicio': '2026-01-01'}
        detalle = f'{self.URL}{self.contrato.pk}/'
        llamadas = {
            'POST': lambda: self.client.post(self.URL, datos, format='json'),
            'PUT': lambda: self.client.put(detalle, datos, format='json'),
            'PATCH': lambda: self.client.patch(detalle, {'horas_semanales_pactadas': 10}, format='json'),
            'DELETE': lambda: self.client.delete(detalle),
        }
        for metodo, llamar in llamadas.items():
            with self.subTest(metodo=metodo):
                self.assertEqual(llamar().status_code, 405)
        self.assertEqual(Contrato.objects.count(), 3)
        self.contrato.refresh_from_db()
        self.assertNotEqual(self.contrato.horas_semanales_pactadas, 10)

    def test_trabajador_recibe_403(self):
        self.client.force_authenticate(crear_usuario('trab@test.cl', '22222222-2'))
        self.assertEqual(self.client.get(self.URL).status_code, 403)
