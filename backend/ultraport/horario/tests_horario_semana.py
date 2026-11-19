"""RF-14: horario semanal (GET /api/horario/semana/)."""
import json
from datetime import date, time, timedelta
from itertools import count
from unittest.mock import patch

from rest_framework.test import APITestCase

from usuarios.models import Maquinaria, Puesto, Rol, Usuario
from usuarios.permissions import Roles
from usuarios.validar_rut import calcular_digito_verificador
from .consultas_horario import SIN_TURNOS
from .models import Area, Asignacion, BloqueTurno, Malla, Turno

URL = '/api/horario/semana/'
LUNES = date(2026, 11, 16)
CAMPOS_PRIVADOS = {'rut', 'correo', 'telefono', 'contrato', 'id_contrato', 'id_usuario'}
SEMANA_VACIA = [[] for _ in range(7)]

_ruts = count(91000000)


def _rut_valido():
    cuerpo = str(next(_ruts))
    return f'{cuerpo}-{calcular_digito_verificador(cuerpo)}'


def _dia(n):
    return LUNES + timedelta(days=n)


def _claves(dato):
    claves = set()
    if isinstance(dato, dict):
        claves |= set(dato)
        dato = list(dato.values())
    if isinstance(dato, list):
        for valor in dato:
            claves |= _claves(valor)
    return claves


def _grupos(data):
    return {g['funcion']: g for g in data['matriz']}


def _fila(data, funcion, usuario):
    filas = [f for f in _grupos(data)[funcion]['trabajadores'] if f['codigo'] == str(usuario.pk)]
    return filas[0] if filas else None


class HorarioSemanaTests(APITestCase):
    def setUp(self):
        self.assertEqual(LUNES.weekday(), 0)
        self.bloque1 = self._bloque(1, 'primer_turno', time(6), time(11))
        self.bloque2 = self._bloque(2, 'segundo_turno', time(14), time(22))
        self.bloque3 = self._bloque(3, 'tercer_turno', time(23), time(7))
        self.naves, _ = Area.objects.get_or_create(nombre_area='Naves y Embarcaciones')
        self.almacenes, _ = Area.objects.get_or_create(nombre_area='Almacenes 1 y 4')
        self.capataz, _ = Puesto.objects.get_or_create(nombre_puesto='Capataz')
        self.operador, _ = Puesto.objects.get_or_create(nombre_puesto='Operador de Payloader')
        self.payloader, _ = Maquinaria.objects.get_or_create(
            nombre_maquinaria='Payloader', defaults={'especialidad': 'payloader'})

        self.admin = self._usuario('admin', Roles.ADMINISTRADOR)
        self.encargado = self._usuario('encargado', Roles.PLANIFICADOR)
        self.trabajador = self._usuario('trabajador', Roles.TRABAJADOR, telefono='912345678')
        self.otro = self._usuario('otro', Roles.TRABAJADOR)

    # ------------------------------------------------------------ helpers

    def _bloque(self, orden, nombre, inicio, termino):
        bloque, _ = BloqueTurno.objects.update_or_create(
            orden_secuencia=orden,
            defaults={'nombre_bloque': nombre, 'hora_inicio': inicio, 'hora_termino': termino})
        return bloque

    def _usuario(self, nombre, rol=None, **extra):
        return Usuario.objects.create_user(
            f'{nombre}@semana.cl', _rut_valido(), nombre.capitalize(), 'Pérez', 'clave-segura-123',
            id_rol=Rol.objects.get(pk=rol) if rol else None, **extra)

    def _malla(self, fecha, publicada=True):
        estado = Malla.Estados.PUBLICADA if publicada else Malla.Estados.BORRADOR
        return Malla.objects.create(fecha=fecha, estado=estado)

    def _turno(self, malla, bloque, puesto=None, area=None, maquina=None):
        return Turno.objects.create(
            id_malla=malla, id_bloque=bloque, id_puesto=puesto or self.capataz,
            id_area=area or self.naves, id_maquinaria_req=maquina, cupos=50)

    def _asignar(self, turno, usuario, estado=Asignacion.Estados.CONFIRMADO):
        return Asignacion.objects.create(id_turno=turno, id_usuario=usuario, estado=estado)

    def _get(self, usuario, desde=LUNES):
        self.client.force_authenticate(usuario)
        return self.client.get(URL, {'desde': desde.isoformat()})

    # ------------------------------------------------------------ 1. rango y acceso

    def test_desde_se_normaliza_al_lunes(self):
        resp = self._get(self.trabajador, desde=_dia(2))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['desde'], LUNES.isoformat())
        self.assertEqual(resp.data['hasta'], _dia(6).isoformat())
        self.assertEqual([d['fecha'] for d in resp.data['dias']], [_dia(i).isoformat() for i in range(7)])

    def test_sin_desde_usa_la_semana_actual(self):
        self.client.force_authenticate(self.trabajador)
        with patch('horario.views_horario.timezone.localdate', return_value=_dia(4)):
            resp = self.client.get(URL)
        self.assertEqual(resp.data['desde'], LUNES.isoformat())

    def test_desde_invalido_400(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.get(URL, {'desde': '2026-13-40'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('desde', resp.data)

    def test_sin_autenticacion_401_y_sin_rol_403(self):
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.assertEqual(self._get(self._usuario('sinrol')).status_code, 403)

    # ------------------------------------------------------------ 2. turnos y descansos

    def test_semana_del_trabajador_con_turnos_y_descansos(self):
        mallas = [self._malla(_dia(i)) for i in range(6)]  # domingo sin malla
        self._asignar(self._turno(mallas[0], self.bloque1), self.trabajador)
        self._asignar(
            self._turno(mallas[2], self.bloque2, self.operador, self.almacenes, self.payloader),
            self.trabajador)

        data = self._get(self.trabajador).data

        self.assertIsNone(data['matriz'])
        self.assertEqual(
            [d['estado'] for d in data['mi_semana']],
            ['turno', 'descanso', 'turno', 'descanso', 'descanso', 'descanso', 'sin_malla'],
        )
        lunes = data['mi_semana'][0]['turnos']
        self.assertEqual(len(lunes), 1)
        self.assertEqual(lunes[0]['orden'], 1)
        self.assertEqual((lunes[0]['hora_inicio'], lunes[0]['hora_termino']), ('06:00', '11:00'))
        self.assertEqual(lunes[0]['fecha_termino'], LUNES.isoformat())
        self.assertEqual(
            (lunes[0]['area'], lunes[0]['funcion'], lunes[0]['maquina']),
            ('Naves y Embarcaciones', 'Capataz', None),
        )
        miercoles = data['mi_semana'][2]['turnos'][0]
        self.assertEqual((miercoles['orden'], miercoles['hora_inicio'], miercoles['hora_termino']), (2, '14:00', '22:00'))
        self.assertEqual((miercoles['funcion'], miercoles['maquina']), ('Operador de Payloader', 'Payloader'))
        self.assertTrue(all(d['sale_de_nocturno'] is None for d in data['mi_semana']))

    # ------------------------------------------------------------ 3. nocturno

    def test_nocturno_del_domingo_cruza_a_la_semana_siguiente(self):
        domingo = self._malla(_dia(6))
        self._malla(_dia(7))  # lunes siguiente publicado, sin turno
        self._asignar(self._turno(domingo, self.bloque3), self.trabajador)

        semana = self._get(self.trabajador).data['mi_semana']
        noche = semana[6]['turnos'][0]
        self.assertEqual(semana[6]['estado'], 'turno')
        self.assertEqual(noche['orden'], 3)
        self.assertTrue(noche['cruza_medianoche'])
        self.assertEqual((noche['hora_inicio'], noche['hora_termino']), ('23:00', '07:00'))
        self.assertEqual(noche['fecha_termino'], _dia(7).isoformat())

        siguiente = self._get(self.trabajador, desde=_dia(7)).data['mi_semana']
        self.assertEqual(siguiente[0]['estado'], 'descanso')
        self.assertEqual(siguiente[0]['turnos'], [])
        self.assertEqual(siguiente[0]['sale_de_nocturno'], '07:00')
        self.assertTrue(all(d['turnos'] == [] for d in siguiente))

    # ------------------------------------------------------------ 4. malla no publicada

    def test_malla_no_publicada(self):
        lunes = self._malla(_dia(0))
        martes = self._malla(_dia(1), publicada=False)
        self._asignar(self._turno(lunes, self.bloque1), self.trabajador)
        self._asignar(self._turno(martes, self.bloque1), self.trabajador, Asignacion.Estados.BORRADOR)

        data = self._get(self.trabajador).data
        self.assertEqual([d['estado'] for d in data['mi_semana']][:2], ['turno', 'no_publicada'])
        self.assertEqual(data['mi_semana'][1]['turnos'], [])

        data = self._get(self.admin).data
        self.assertEqual(data['dias'][1]['malla']['estado'], 'borrador')
        self.assertFalse(data['dias'][1]['visible'])
        self.assertEqual(_fila(data, 'Capataz', self.trabajador)['turnos'][:2], [[1], []])

        data = self._get(self.encargado).data
        self.assertTrue(data['puede_editar'])
        self.assertTrue(data['dias'][1]['visible'])
        self.assertFalse(data['dias'][1]['publicada'])
        self.assertEqual(_fila(data, 'Capataz', self.trabajador)['turnos'][:2], [[1], [1]])

    # ------------------------------------------------------------ 5. privacidad

    def test_trabajador_no_ve_datos_ajenos(self):
        malla = self._malla(_dia(0))
        turno = self._turno(malla, self.bloque1)
        self._asignar(turno, self.trabajador)
        self._asignar(turno, self.otro)
        self._asignar(self._turno(malla, self.bloque2), self.otro)

        resp = self._get(self.trabajador)
        self.assertIsNone(resp.data['matriz'])
        cuerpo = resp.content.decode()
        self.assertNotIn('Otro', cuerpo)
        self.assertNotIn('codigo', cuerpo)
        self.assertNotIn(self.otro.correo, cuerpo)
        self.assertEqual(len(resp.data['mi_semana'][0]['turnos']), 1)

    def test_ningun_rol_recibe_campos_privados(self):
        malla = self._malla(_dia(0))
        self._asignar(self._turno(malla, self.bloque1), self.trabajador)
        for usuario in (self.trabajador, self.encargado, self.admin):
            with self.subTest(usuario=usuario.correo):
                resp = self._get(usuario)
                self.assertFalse(_claves(resp.data) & CAMPOS_PRIVADOS)
                cuerpo = json.loads(resp.content)
                self.assertNotIn(self.trabajador.rut, json.dumps(cuerpo))
                self.assertNotIn(self.trabajador.correo, json.dumps(cuerpo))

    # ------------------------------------------------------------ 6. matriz

    def test_matriz_agrupada_por_funcion(self):
        lunes, martes = self._malla(_dia(0)), self._malla(_dia(1))
        self._asignar(self._turno(lunes, self.bloque1), self.trabajador)
        self._asignar(self._turno(lunes, self.bloque3), self.trabajador)
        self._asignar(self._turno(martes, self.bloque2, self.operador, self.almacenes), self.trabajador)
        self._asignar(self._turno(lunes, self.bloque1), self.otro)
        rechazado = self._usuario('rechazado', Roles.TRABAJADOR)
        reemplazado = self._usuario('reemplazado', Roles.TRABAJADOR)
        turno_martes = self._turno(martes, self.bloque1)
        self._asignar(turno_martes, rechazado, Asignacion.Estados.RECHAZADO)
        self._asignar(turno_martes, reemplazado, Asignacion.Estados.REEMPLAZADO)

        data = self._get(self.encargado).data

        self.assertIsNone(data['mi_semana'])
        self.assertEqual(
            [g['funcion'] for g in data['matriz']],
            ['Capataz', 'Operador de Payloader', SIN_TURNOS],
        )
        capataz = _grupos(data)['Capataz']
        self.assertFalse(capataz['sin_turnos'])
        self.assertEqual(
            [f['codigo'] for f in capataz['trabajadores']],
            sorted([str(self.trabajador.pk), str(self.otro.pk)], key=int),
        )
        self.assertEqual(_fila(data, 'Capataz', self.trabajador)['turnos'], [[1, 3]] + [[]] * 6)
        self.assertEqual(_fila(data, 'Capataz', self.otro)['turnos'], [[1]] + [[]] * 6)
        self.assertEqual(_fila(data, 'Operador de Payloader', self.trabajador)['turnos'], [[], [2]] + [[]] * 5)
        con_turnos = {
            f['codigo'] for g in data['matriz'] if not g['sin_turnos'] for f in g['trabajadores']
        }
        self.assertNotIn(str(rechazado.pk), con_turnos)
        self.assertNotIn(str(reemplazado.pk), con_turnos)

    # ------------------------------------------------------------ 8. sin turnos

    def test_grupo_sin_turnos_incluye_activos_y_excluye_inactivos(self):
        self._asignar(self._turno(self._malla(_dia(0)), self.bloque1), self.trabajador)
        libre = self._usuario('libre', Roles.TRABAJADOR)
        inactivo = self._usuario('inactivo', Roles.TRABAJADOR, is_active=False, estado='inactivo')

        data = self._get(self.admin).data
        grupo = data['matriz'][-1]
        self.assertEqual(grupo['funcion'], SIN_TURNOS)
        self.assertTrue(grupo['sin_turnos'])
        codigos = [f['codigo'] for f in grupo['trabajadores']]
        self.assertEqual(codigos, sorted([str(self.otro.pk), str(libre.pk)], key=int))
        self.assertNotIn(str(inactivo.pk), codigos)
        self.assertNotIn(str(self.trabajador.pk), codigos)
        # Encargado y administrador no son rol Trabajador: no aparecen.
        self.assertNotIn(str(self.encargado.pk), codigos)
        for fila in grupo['trabajadores']:
            self.assertEqual(set(fila), {'codigo', 'nombre', 'turnos'})
            self.assertEqual(fila['turnos'], SEMANA_VACIA)
        self.assertIn('Libre Pérez', [f['nombre'] for f in grupo['trabajadores']])

    def test_turnos_solo_en_borrador_cuentan_como_sin_turnos_para_admin(self):
        borrador = self._malla(_dia(1), publicada=False)
        self._asignar(self._turno(borrador, self.bloque1), self.trabajador, Asignacion.Estados.BORRADOR)

        sin_turnos_admin = [f['codigo'] for f in self._get(self.admin).data['matriz'][-1]['trabajadores']]
        self.assertIn(str(self.trabajador.pk), sin_turnos_admin)

        sin_turnos_encargado = [f['codigo'] for f in self._get(self.encargado).data['matriz'][-1]['trabajadores']]
        self.assertNotIn(str(self.trabajador.pk), sin_turnos_encargado)

    def test_sin_trabajadores_libres_no_hay_grupo_sin_turnos(self):
        malla = self._malla(_dia(0))
        turno = self._turno(malla, self.bloque1)
        self._asignar(turno, self.trabajador)
        self._asignar(turno, self.otro)
        self.assertNotIn(SIN_TURNOS, [g['funcion'] for g in self._get(self.encargado).data['matriz']])

    # ------------------------------------------------------------ 7. consultas

    def test_cantidad_de_consultas_constante(self):
        mallas = [self._malla(_dia(i)) for i in range(7)]
        turnos = [self._turno(m, self.bloque1) for m in mallas]
        self._asignar(turnos[0], self.trabajador)
        self._asignar(turnos[0], self.otro)

        def medir():
            self.client.force_authenticate(self.trabajador)
            with self.assertNumQueries(3):
                self.client.get(URL, {'desde': LUNES.isoformat()})
            self.client.force_authenticate(self.encargado)
            with self.assertNumQueries(4):
                return self.client.get(URL, {'desde': LUNES.isoformat()})

        medir()

        for i in range(20):
            extra = self._usuario(f'extra{i}', Roles.TRABAJADOR)
            for turno in turnos:
                self._asignar(turno, extra)
        for i in range(5):
            self._usuario(f'libre{i}', Roles.TRABAJADOR)

        resp = medir()
        grupos = _grupos(resp.data)
        self.assertEqual(len(grupos['Capataz']['trabajadores']), 22)
        self.assertEqual(len(grupos[SIN_TURNOS]['trabajadores']), 5)
