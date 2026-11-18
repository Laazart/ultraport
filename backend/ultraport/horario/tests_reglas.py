from datetime import date, time, timedelta
from itertools import count

from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from usuarios.models import Contrato, Puesto, Rol, Usuario, UsuarioPuesto
from usuarios.permissions import Roles
from usuarios.validar_rut import calcular_digito_verificador
from .models import Asignacion, BloqueTurno, Malla, NotificacionInasistencia, Turno
from .reglas import validar_asignacion

LUNES = date(2026, 11, 16)
MSG_CONSECUTIVAS = 'noche(s) seguida(s)'
MSG_SEMANA = 'noches a la semana'
MSG_DESCANSO = 'descanso mínimo'
MSG_TRASLAPE = 'Se traslapa'
MSG_INASISTENCIA = 'inasistencia aprobada'
MSG_PACTADAS = 'h pactadas'

_ruts = count(80000000)


def _rut_valido():
    cuerpo = str(next(_ruts))
    return f'{cuerpo}-{calcular_digito_verificador(cuerpo)}'


def _dia(n):
    return LUNES + timedelta(days=n)


class BloquesOficialesTests(TestCase):
    def test_migracion_deja_horarios_oficiales(self):
        horarios = {
            b.orden_secuencia: (b.hora_inicio, b.hora_termino)
            for b in BloqueTurno.objects.all()
        }
        self.assertEqual(horarios, {
            1: (time(8), time(15, 30)),
            2: (time(15, 30), time(23)),
            3: (time(23), time(6, 30)),
        })
        self.assertTrue(BloqueTurno.objects.get(orden_secuencia=3).es_nocturno)


class ReglasAsignacionTests(TestCase):
    def setUp(self):
        self.assertEqual(LUNES.weekday(), 0)
        self.primero = BloqueTurno.objects.get(orden_secuencia=1)
        self.segundo = BloqueTurno.objects.get(orden_secuencia=2)
        self.tercero = BloqueTurno.objects.get(orden_secuencia=3)
        self.puesto, _ = Puesto.objects.get_or_create(nombre_puesto='Capataz')
        self.rol = Rol.objects.get(pk=Roles.TRABAJADOR)
        self.bono = self._contrato('bono_turno', semana=2, consecutivas=1, extra=False)
        self.cppt = self._contrato('cppt', semana=None, consecutivas=3)
        self.eventual = self._contrato('eventual', semana=None, consecutivas=None)

    def _contrato(self, tipo, semana, consecutivas, extra=True):
        return Contrato.objects.create(
            tipo=tipo, turno_habitual='rotativo', horas_semanales_pactadas=42,
            permite_horas_extra=extra, fecha_inicio=date(2026, 1, 1),
            max_noches_semana=semana, max_noches_consecutivas=consecutivas,
        )

    def _trabajador(self, contrato):
        rut = _rut_valido()
        usuario = Usuario.objects.create_user(
            f'{rut}@test.cl', rut, 'Juan', 'Pérez', 'clave-segura-123',
            id_rol=self.rol, id_contrato=contrato,
        )
        UsuarioPuesto.objects.create(id_usuario=usuario, id_puesto=self.puesto)
        return usuario

    def _turno(self, fecha, bloque):
        malla, _ = Malla.objects.get_or_create(fecha=fecha)
        return Turno.objects.create(
            id_malla=malla, id_bloque=bloque, id_puesto=self.puesto, cupos=10,
        )

    def _asignar(self, usuario, fecha, bloque):
        """Valida y, si no hay errores, crea la asignación. Devuelve los errores."""
        turno = self._turno(fecha, bloque)
        errores = validar_asignacion(usuario, turno)
        if not errores:
            Asignacion.objects.create(id_turno=turno, id_usuario=usuario)
        return errores

    def assertPermitido(self, errores):
        self.assertEqual(errores, [])

    def assertBloqueado(self, errores, fragmento):
        self.assertTrue(
            any(fragmento in e for e in errores),
            f'Se esperaba un error con {fragmento!r}, se obtuvo {errores!r}',
        )

    # --- bono_turno ---

    def test_bono_turno_dos_noches_seguidas_bloqueado(self):
        t = self._trabajador(self.bono)
        self.assertPermitido(self._asignar(t, _dia(0), self.tercero))
        self.assertBloqueado(self._asignar(t, _dia(1), self.tercero), MSG_CONSECUTIVAS)

    def test_bono_turno_tercera_noche_semanal_bloqueada(self):
        t = self._trabajador(self.bono)
        self.assertPermitido(self._asignar(t, _dia(0), self.tercero))
        self.assertPermitido(self._asignar(t, _dia(2), self.tercero))
        errores = self._asignar(t, _dia(4), self.tercero)
        self.assertBloqueado(errores, MSG_SEMANA)
        self.assertFalse(any(MSG_CONSECUTIVAS in e for e in errores))

    def test_bono_turno_supera_horas_pactadas_bloqueado(self):
        t = self._trabajador(self.bono)
        # 5 x 7,5 h = 37,5 h dentro de las 42 pactadas; el sexto llegaría a 45 h.
        for n in range(5):
            self.assertPermitido(self._asignar(t, _dia(n), self.primero))
        self.assertBloqueado(self._asignar(t, _dia(5), self.primero), MSG_PACTADAS)

    # --- cppt ---

    def test_cppt_maximo_tres_noches_seguidas_sin_limite_semanal(self):
        t = self._trabajador(self.cppt)
        for n in (0, 1, 2):
            self.assertPermitido(self._asignar(t, _dia(n), self.tercero))
        self.assertBloqueado(self._asignar(t, _dia(3), self.tercero), MSG_CONSECUTIVAS)
        for n in (4, 5, 6):
            self.assertPermitido(self._asignar(t, _dia(n), self.tercero))

    def test_noches_seguidas_cuentan_de_domingo_a_lunes(self):
        t = self._trabajador(self.cppt)
        for n in (4, 5, 6):  # viernes, sábado, domingo
            self.assertPermitido(self._asignar(t, _dia(n), self.tercero))
        # Lunes siguiente: otra semana, pero cuarta noche seguida.
        self.assertBloqueado(self._asignar(t, _dia(7), self.tercero), MSG_CONSECUTIVAS)

    def test_bono_turno_domingo_y_lunes_son_consecutivas(self):
        t = self._trabajador(self.bono)
        self.assertPermitido(self._asignar(t, _dia(6), self.tercero))
        self.assertBloqueado(self._asignar(t, _dia(7), self.tercero), MSG_CONSECUTIVAS)

    # --- eventual ---

    def test_eventual_siete_noches_permitido(self):
        t = self._trabajador(self.eventual)
        for n in range(7):
            self.assertPermitido(self._asignar(t, _dia(n), self.tercero))

    # --- descanso y traslape ---

    def test_tercero_y_primero_del_dia_siguiente_bloqueado(self):
        t = self._trabajador(self.eventual)
        self.assertPermitido(self._asignar(t, _dia(0), self.tercero))
        # 06:30 -> 08:00 = 1,5 h de descanso.
        self.assertBloqueado(self._asignar(t, _dia(1), self.primero), MSG_DESCANSO)

    @override_settings(HORARIO_DESCANSO_MINIMO_HORAS=12)
    def test_primero_y_tercero_mismo_dia_con_descanso_12_bloqueado(self):
        t = self._trabajador(self.eventual)
        self.assertPermitido(self._asignar(t, _dia(0), self.primero))
        # 15:30 -> 23:00 = 7,5 h de descanso.
        self.assertBloqueado(self._asignar(t, _dia(0), self.tercero), MSG_DESCANSO)

    def test_primero_y_tercero_mismo_dia_permitido_por_defecto(self):
        t = self._trabajador(self.eventual)
        self.assertPermitido(self._asignar(t, _dia(0), self.primero))
        # 15:30 -> 23:00 = 7,5 h, justo el descanso mínimo configurado.
        self.assertPermitido(self._asignar(t, _dia(0), self.tercero))

    def test_segundo_y_primero_del_dia_siguiente_permitido(self):
        t = self._trabajador(self.eventual)
        self.assertPermitido(self._asignar(t, _dia(0), self.segundo))
        # 23:00 -> 08:00 = 9 h de descanso.
        self.assertPermitido(self._asignar(t, _dia(1), self.primero))

    @override_settings(HORARIO_DESCANSO_MINIMO_HORAS=0)
    def test_mismo_bloque_en_otro_turno_se_traslapa(self):
        t = self._trabajador(self.eventual)
        self.assertPermitido(self._asignar(t, _dia(0), self.primero))
        errores = self._asignar(t, _dia(0), self.primero)
        self.assertBloqueado(errores, MSG_TRASLAPE)

    # --- inasistencia ---

    def _inasistencia(self, usuario, inicio, fin=None, estado=NotificacionInasistencia.APROBADO):
        return NotificacionInasistencia.objects.create(
            id_usuario=usuario, motivo='Licencia', fecha_inicio=inicio,
            fecha_fin=fin, estado=estado,
        )

    def test_inasistencia_del_dia_siguiente_bloquea_noche_anterior(self):
        t = self._trabajador(self.eventual)
        self._inasistencia(t, _dia(1), _dia(3))
        self.assertBloqueado(self._asignar(t, _dia(0), self.tercero), MSG_INASISTENCIA)
        # El turno de día de esa misma fecha no se ve afectado.
        self.assertPermitido(self._asignar(t, _dia(0), self.primero))

    def test_inasistencia_de_un_dia_sin_fecha_fin_bloquea_noche_anterior(self):
        t = self._trabajador(self.eventual)
        self._inasistencia(t, _dia(1))
        self.assertBloqueado(self._asignar(t, _dia(0), self.tercero), MSG_INASISTENCIA)

    def test_inasistencia_pendiente_no_bloquea(self):
        t = self._trabajador(self.eventual)
        self._inasistencia(t, _dia(1), estado=NotificacionInasistencia.PENDIENTE)
        self.assertPermitido(self._asignar(t, _dia(0), self.tercero))


class ContratoNochesApiTests(APITestCase):
    URL = '/api/contratos/'

    def setUp(self):
        rut = _rut_valido()
        admin = Usuario.objects.create_user(
            'admin-contratos@test.cl', rut, 'Ana', 'Soto', 'clave-segura-123',
            id_rol=Rol.objects.get(pk=Roles.ADMINISTRADOR),
        )
        self.client.force_authenticate(admin)

    def _payload(self, **extra):
        datos = {
            'tipo': 'eventual', 'turno_habitual': 'rotativo',
            'horas_semanales_pactadas': 42, 'fecha_inicio': '2026-01-01',
        }
        datos.update(extra)
        return datos

    def test_acepta_null_como_sin_limite(self):
        resp = self.client.post(self.URL, self._payload(
            max_noches_consecutivas=None, max_noches_semana=None), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertIsNone(resp.data['max_noches_consecutivas'])
        self.assertIsNone(resp.data['max_noches_semana'])

    def test_campos_opcionales_quedan_null(self):
        resp = self.client.post(self.URL, self._payload(), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        contrato = Contrato.objects.get(pk=resp.data['id_contrato'])
        self.assertIsNone(contrato.max_noches_consecutivas)
        self.assertIsNone(contrato.max_noches_semana)

    def test_guarda_y_expone_limites(self):
        resp = self.client.post(self.URL, self._payload(
            tipo='bono_turno', max_noches_consecutivas=1, max_noches_semana=2), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        detalle = self.client.get(f"{self.URL}{resp.data['id_contrato']}/").data
        self.assertEqual(detalle['max_noches_consecutivas'], 1)
        self.assertEqual(detalle['max_noches_semana'], 2)

    def test_rechaza_valores_no_positivos_o_no_enteros(self):
        for campo in ('max_noches_consecutivas', 'max_noches_semana'):
            for valor in (0, -1, 'abc', 2.5):
                with self.subTest(campo=campo, valor=valor):
                    resp = self.client.post(self.URL, self._payload(**{campo: valor}), format='json')
                    self.assertEqual(resp.status_code, 400)
                    self.assertIn(campo, resp.data)
