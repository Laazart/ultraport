from datetime import date, time
from itertools import count
from unittest.mock import patch

from rest_framework.test import APITestCase

from usuarios.models import Maquinaria, Puesto, Rol, Usuario
from usuarios.permissions import Roles
from .models import Area, Asignacion, BloqueTurno, Malla, Turno

URL = '/api/horario/dia/'
FECHA = date(2026, 10, 24)
CAMPOS_PRIVADOS = {'rut', 'correo', 'telefono', 'contrato', 'id_contrato', 'id_usuario'}

_ruts = count(10000000)


def _claves(dato):
    claves = set()
    if isinstance(dato, dict):
        claves |= set(dato)
        dato = list(dato.values())
    if isinstance(dato, list):
        for valor in dato:
            claves |= _claves(valor)
    return claves


def _filas(data):
    return [
        trabajador
        for bloque in data['bloques']
        for area in bloque['areas']
        for faena in area['faenas']
        for trabajador in faena['trabajadores']
    ]


class HorarioDiaTests(APITestCase):
    def setUp(self):
        self.bloque1 = BloqueTurno.objects.create(
            nombre_bloque='primer_turno', hora_inicio=time(6), hora_termino=time(11), orden_secuencia=1)
        self.bloque2 = BloqueTurno.objects.create(
            nombre_bloque='segundo_turno', hora_inicio=time(14), hora_termino=time(22), orden_secuencia=2)
        self.bloque3 = BloqueTurno.objects.create(
            nombre_bloque='tercer_turno', hora_inicio=time(23), hora_termino=time(7), orden_secuencia=3)
        self.naves = Area.objects.create(nombre_area='Naves y Embarcaciones')
        self.almacenes = Area.objects.create(nombre_area='Almacenes 1 y 4')
        self.capataz = Puesto.objects.create(nombre_puesto='Capataz')
        self.operador = Puesto.objects.create(nombre_puesto='Operador de Payloader')
        self.payloader = Maquinaria.objects.create(nombre_maquinaria='Payloader', especialidad='Carga')

        self.admin = self._usuario('admin', Roles.ADMINISTRADOR)
        self.encargado = self._usuario('encargado', Roles.PLANIFICADOR)
        self.trabajador = self._usuario('trabajador', Roles.TRABAJADOR, telefono='912345678')
        self.otro = self._usuario('otro', Roles.TRABAJADOR)

        self.malla = Malla.objects.create(fecha=FECHA, estado=Malla.Estados.PUBLICADA)

    def _usuario(self, nombre, rol=None, **extra):
        return Usuario.objects.create_user(
            f'{nombre}@test.cl', f'{next(_ruts)}-0', nombre.capitalize(), 'Pérez', 'clave-segura-123',
            id_rol=Rol.objects.get(pk=rol) if rol else None, **extra)

    def _turno(self, bloque, puesto, area=None, maquina=None):
        return Turno.objects.create(
            id_malla=self.malla, id_bloque=bloque, id_puesto=puesto,
            id_area=area, id_maquinaria_req=maquina, cupos=50)

    def _asignar(self, turno, usuario, estado=Asignacion.Estados.BORRADOR):
        return Asignacion.objects.create(id_turno=turno, id_usuario=usuario, estado=estado)

    def _get(self, usuario, fecha=FECHA):
        self.client.force_authenticate(usuario)
        return self.client.get(URL, {'fecha': fecha.isoformat()})

    def _escenario_basico(self):
        self._asignar(self._turno(self.bloque3, self.capataz, self.naves), self.trabajador)
        self._asignar(self._turno(self.bloque1, self.operador, self.almacenes, self.payloader), self.otro)

    def test_sin_autenticacion_401(self):
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 401)

    def test_usuario_sin_rol_403(self):
        resp = self._get(self._usuario('sinrol'))
        self.assertEqual(resp.status_code, 403)

    def test_los_tres_roles_ven_asignaciones_de_todos(self):
        self._escenario_basico()
        esperados = {str(self.trabajador.pk), str(self.otro.pk)}
        for usuario in (self.admin, self.encargado, self.trabajador):
            with self.subTest(usuario=usuario.correo):
                resp = self._get(usuario)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual({fila['codigo'] for fila in _filas(resp.data)}, esperados)

    def test_no_expone_datos_sensibles(self):
        self._escenario_basico()
        for usuario in (self.admin, self.encargado, self.trabajador):
            with self.subTest(usuario=usuario.correo):
                resp = self._get(usuario)
                self.assertFalse(_claves(resp.json()) & CAMPOS_PRIVADOS)
                contenido = resp.content.decode()
                for persona in (self.trabajador, self.otro):
                    self.assertNotIn(persona.rut, contenido)
                    self.assertNotIn(persona.correo, contenido)
                self.assertNotIn(self.trabajador.telefono, contenido)

    def test_puede_editar_solo_encargado(self):
        self.assertFalse(self._get(self.admin).data['puede_editar'])
        self.assertTrue(self._get(self.encargado).data['puede_editar'])
        self.assertFalse(self._get(self.trabajador).data['puede_editar'])

    def test_trabajador_ve_su_turno_y_su_fila(self):
        self._escenario_basico()
        data = self._get(self.trabajador).data
        self.assertEqual(data['mi_turno'], {
            'id_bloque': self.bloque3.pk, 'orden': 3, 'hora_inicio': '23:00', 'hora_termino': '07:00',
            'cruza_medianoche': True, 'area': 'Naves y Embarcaciones', 'funcion': 'Capataz', 'maquina': None,
        })
        self.assertEqual([fila['codigo'] for fila in _filas(data) if fila['es_mio']], [str(self.trabajador.pk)])

    def test_admin_y_encargado_sin_mi_turno(self):
        self._escenario_basico()
        for usuario in (self.admin, self.encargado):
            with self.subTest(usuario=usuario.correo):
                data = self._get(usuario).data
                self.assertIsNone(data['mi_turno'])
                self.assertFalse(any(fila['es_mio'] for fila in _filas(data)))

    def test_fecha_sin_malla(self):
        resp = self._get(self.trabajador, fecha=date(2026, 10, 25))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data['malla'])
        self.assertFalse(resp.data['publicada'])
        self.assertIsNone(resp.data['mi_turno'])
        self.assertEqual([bloque['orden'] for bloque in resp.data['bloques']], [1, 2, 3])
        for bloque in resp.data['bloques']:
            self.assertEqual(bloque['total'], 0)
            self.assertEqual(bloque['areas'], [])

    def test_malla_borrador(self):
        self.malla.estado = Malla.Estados.BORRADOR
        self.malla.save()
        self._escenario_basico()
        for usuario in (self.admin, self.trabajador):
            with self.subTest(usuario=usuario.correo):
                data = self._get(usuario).data
                self.assertEqual(data['malla'], {'id_malla': self.malla.pk, 'estado': 'borrador'})
                self.assertFalse(data['publicada'])
                self.assertEqual(_filas(data), [])
                self.assertIsNone(data['mi_turno'])
        data = self._get(self.encargado).data
        self.assertFalse(data['publicada'])
        self.assertEqual(len(_filas(data)), 2)

    def test_rechazado_y_reemplazado_no_aparecen(self):
        turno = self._turno(self.bloque1, self.capataz, self.naves)
        self._asignar(turno, self.trabajador, Asignacion.Estados.CONFIRMADO)
        self._asignar(turno, self.otro, Asignacion.Estados.RECHAZADO)
        self._asignar(turno, self.admin, Asignacion.Estados.REEMPLAZADO)
        data = self._get(self.encargado).data
        self.assertEqual([fila['codigo'] for fila in _filas(data)], [str(self.trabajador.pk)])
        self.assertEqual(data['bloques'][0]['total'], 1)

    def test_cruza_medianoche_por_bloque(self):
        bloques = self._get(self.trabajador).data['bloques']
        self.assertEqual({b['orden']: b['cruza_medianoche'] for b in bloques}, {1: False, 2: False, 3: True})
        self.assertEqual((bloques[2]['hora_inicio'], bloques[2]['hora_termino']), ('23:00', '07:00'))

    def test_maquina_sale_del_turno(self):
        self._escenario_basico()
        maquinas = {fila['codigo']: fila['maquina'] for fila in _filas(self._get(self.admin).data)}
        self.assertEqual(maquinas, {str(self.otro.pk): 'Payloader', str(self.trabajador.pk): None})

    def test_agrupacion_por_area_faena_y_orden_por_codigo(self):
        turno_almacenes = self._turno(self.bloque1, self.operador, self.almacenes, self.payloader)
        self._asignar(turno_almacenes, self.otro)
        self._asignar(turno_almacenes, self.trabajador)
        self._asignar(self._turno(self.bloque1, self.capataz), self.admin)
        self._asignar(self._turno(self.bloque1, self.capataz, self.naves), self.encargado)

        bloques = self._get(self.encargado).data['bloques']
        primero = bloques[0]
        self.assertEqual(primero['total'], 4)
        self.assertEqual(
            [area['area'] for area in primero['areas']],
            ['Almacenes 1 y 4', 'Naves y Embarcaciones', 'Sin área'],
        )
        almacenes = primero['areas'][0]
        self.assertEqual([faena['faena'] for faena in almacenes['faenas']], ['General'])
        self.assertEqual(
            [fila['codigo'] for fila in almacenes['faenas'][0]['trabajadores']],
            [str(self.trabajador.pk), str(self.otro.pk)],
        )
        self.assertEqual([bloque['total'] for bloque in bloques[1:]], [0, 0])

    def test_fecha_invalida_400(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.get(URL, {'fecha': '2026-13-40'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fecha', resp.data)

    def test_sin_fecha_usa_localdate(self):
        self._escenario_basico()
        self.client.force_authenticate(self.trabajador)
        with patch('horario.views_horario.timezone.localdate', return_value=FECHA) as localdate:
            resp = self.client.get(URL)
        localdate.assert_called_once()
        self.assertEqual(resp.data['fecha'], FECHA.isoformat())
        self.assertEqual(len(_filas(resp.data)), 2)

    def test_generado_en_formato_hora(self):
        self.assertRegex(self._get(self.trabajador).data['generado_en'], r'^\d{2}:\d{2}$')

    def test_cantidad_de_consultas_constante(self):
        turno = self._turno(self.bloque1, self.operador, self.almacenes, self.payloader)
        self._asignar(turno, self.trabajador)
        self._asignar(turno, self.otro)
        self.client.force_authenticate(self.trabajador)
        with self.assertNumQueries(3):
            self.client.get(URL, {'fecha': FECHA.isoformat()})

        for i in range(18):
            self._asignar(turno, self._usuario(f'extra{i}', Roles.TRABAJADOR))
        with self.assertNumQueries(3):
            resp = self.client.get(URL, {'fecha': FECHA.isoformat()})

        codigos = [fila['codigo'] for fila in _filas(resp.data)]
        self.assertEqual(len(codigos), 20)
        self.assertEqual(codigos, sorted(codigos, key=int))
