"""CU-7: edición de mallas publicadas, cupos como referencia, mover, candidatos y autocompletar."""
from collections import Counter
from datetime import date, timedelta
from itertools import count

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from usuarios.models import (
    Contrato, Puesto, Rol, TipoLicencia, Usuario, UsuarioLicencia, UsuarioPuesto,
)
from usuarios.permissions import Roles
from usuarios.validar_rut import calcular_digito_verificador
from .models import Asignacion, BloqueTurno, Malla, NotificacionInasistencia, Turno
from .serializers import TurnoSerializer
from .services import (
    asignar_usuario, autocompletar_malla, mover_asignacion, publicar_malla, quitar_asignacion,
)

LUNES = date(2026, 11, 16)
MSG_DESCANSO = 'descanso mínimo'
MSG_INASISTENCIA = 'inasistencia aprobada'
MSG_CONSECUTIVAS = 'noche(s) seguida(s)'
MSG_LICENCIA = 'licencia vigente'

_ruts = count(70000000)
_apellidos = count(1)


def _rut_valido():
    cuerpo = str(next(_ruts))
    return f'{cuerpo}-{calcular_digito_verificador(cuerpo)}'


def _dia(n):
    return LUNES + timedelta(days=n)


class _BaseMalla:
    """Helpers compartidos por los tests de servicios y de API."""

    def _preparar(self):
        self.primero = BloqueTurno.objects.get(orden_secuencia=1)
        self.segundo = BloqueTurno.objects.get(orden_secuencia=2)
        self.tercero = BloqueTurno.objects.get(orden_secuencia=3)
        self.puesto = Puesto.objects.create(nombre_puesto='Puesto prueba CU-7')
        self.rol_trabajador = Rol.objects.get(pk=Roles.TRABAJADOR)
        self.eventual = self._contrato('eventual', semana=None, consecutivas=None)
        self.bono = self._contrato('bono_turno', semana=2, consecutivas=1, extra=False)

    def _contrato(self, tipo, semana, consecutivas, extra=True):
        return Contrato.objects.create(
            tipo=tipo, turno_habitual='rotativo', horas_semanales_pactadas=42,
            permite_horas_extra=extra, fecha_inicio=date(2026, 1, 1),
            max_noches_semana=semana, max_noches_consecutivas=consecutivas,
        )

    def _trabajador(self, contrato=None, con_puesto=True):
        rut = _rut_valido()
        usuario = Usuario.objects.create_user(
            f'{rut}@test.cl', rut, 'Juan', f'Apellido{next(_apellidos):03d}', 'clave-segura-123',
            id_rol=self.rol_trabajador, id_contrato=contrato or self.eventual,
        )
        if con_puesto:
            UsuarioPuesto.objects.create(id_usuario=usuario, id_puesto=self.puesto)
        return usuario

    def _malla(self, fecha, publicada=False):
        estado = Malla.Estados.PUBLICADA if publicada else Malla.Estados.BORRADOR
        malla, _ = Malla.objects.get_or_create(fecha=fecha, defaults={'estado': estado})
        return malla

    def _turno(self, malla, bloque, cupos=2, **extra):
        return Turno.objects.create(
            id_malla=malla, id_bloque=bloque, id_puesto=self.puesto, cupos=cupos, **extra,
        )

    def _asignacion(self, turno, usuario, estado=Asignacion.Estados.BORRADOR):
        return Asignacion.objects.create(id_turno=turno, id_usuario=usuario, estado=estado)

    def _inasistencia(self, usuario, inicio, fin=None):
        return NotificacionInasistencia.objects.create(
            id_usuario=usuario, motivo='Licencia médica', fecha_inicio=inicio,
            fecha_fin=fin, estado=NotificacionInasistencia.APROBADO,
        )

    def _activas(self, **filtros):
        return Asignacion.objects.filter(estado__in=['borrador', 'confirmado'], **filtros)

    def assertErrorCon(self, ctx, fragmento):
        texto = str(ctx.exception.detail)
        self.assertIn(fragmento, texto)


class AsignarYQuitarTests(_BaseMalla, TestCase):
    def setUp(self):
        self._preparar()

    def test_asignar_en_malla_publicada_queda_confirmado(self):
        turno = self._turno(self._malla(_dia(0), publicada=True), self.primero)
        asignacion = asignar_usuario(turno, self._trabajador())
        self.assertEqual(asignacion.estado, Asignacion.Estados.CONFIRMADO)

    def test_asignar_en_borrador_queda_borrador(self):
        turno = self._turno(self._malla(_dia(0)), self.primero)
        asignacion = asignar_usuario(turno, self._trabajador())
        self.assertEqual(asignacion.estado, Asignacion.Estados.BORRADOR)

    def test_asignar_sobre_el_cupo_se_permite(self):
        turno = self._turno(self._malla(_dia(0)), self.primero, cupos=1)
        asignar_usuario(turno, self._trabajador())
        asignar_usuario(turno, self._trabajador())
        self.assertEqual(self._activas(id_turno=turno).count(), 2)

    def test_asignar_sigue_validando_descanso(self):
        t = self._trabajador()
        self._asignacion(self._turno(self._malla(_dia(0)), self.tercero), t)
        turno = self._turno(self._malla(_dia(1)), self.primero)
        with self.assertRaises(ValidationError) as ctx:
            asignar_usuario(turno, t)
        self.assertErrorCon(ctx, MSG_DESCANSO)

    def test_quitar_en_borrador_elimina(self):
        turno = self._turno(self._malla(_dia(0)), self.primero)
        a = self._asignacion(turno, self._trabajador())
        quitar_asignacion(a)
        self.assertFalse(Asignacion.objects.filter(pk=a.pk).exists())

    def test_quitar_en_publicada_queda_reemplazado_y_sale_de_la_grilla(self):
        turno = self._turno(self._malla(_dia(0), publicada=True), self.primero)
        a = self._asignacion(turno, self._trabajador(), Asignacion.Estados.CONFIRMADO)
        quitar_asignacion(a)
        a.refresh_from_db()
        self.assertEqual(a.estado, Asignacion.Estados.REEMPLAZADO)
        self.assertEqual(TurnoSerializer(turno).data['asignaciones'], [])


class MoverTests(_BaseMalla, TestCase):
    def setUp(self):
        self._preparar()

    def test_mover_en_publicada_deja_historial(self):
        malla = self._malla(_dia(0), publicada=True)
        origen = self._turno(malla, self.primero)
        destino = self._turno(malla, self.tercero)
        t = self._trabajador()
        a = self._asignacion(origen, t, Asignacion.Estados.CONFIRMADO)

        nueva = mover_asignacion(a, destino)

        a.refresh_from_db()
        self.assertEqual(a.estado, Asignacion.Estados.REEMPLAZADO)
        self.assertEqual(a.id_turno, origen)
        self.assertNotEqual(nueva.pk, a.pk)
        self.assertEqual(nueva.id_turno, destino)
        self.assertEqual(nueva.estado, Asignacion.Estados.CONFIRMADO)

    def test_mover_en_borrador_cambia_turno_sin_crear_filas(self):
        malla = self._malla(_dia(0))
        origen = self._turno(malla, self.primero)
        destino = self._turno(malla, self.tercero)
        a = self._asignacion(origen, self._trabajador())

        resultado = mover_asignacion(a, destino)

        self.assertEqual(resultado.pk, a.pk)
        self.assertEqual(resultado.id_turno, destino)
        self.assertEqual(Asignacion.objects.count(), 1)

    def test_mover_primero_a_segundo_mismo_dia_excluye_el_origen(self):
        # Sin excluir el origen habría 0 h de descanso entre 15:30 y 15:30.
        malla = self._malla(_dia(0))
        origen = self._turno(malla, self.primero)
        destino = self._turno(malla, self.segundo)
        a = self._asignacion(origen, self._trabajador())
        self.assertEqual(mover_asignacion(a, destino).id_turno, destino)

    def test_mover_respeta_descanso(self):
        t = self._trabajador()
        self._asignacion(self._turno(self._malla(_dia(-1)), self.tercero), t)
        malla = self._malla(_dia(0))
        a = self._asignacion(self._turno(malla, self.segundo), t)
        destino = self._turno(malla, self.primero)
        with self.assertRaises(ValidationError) as ctx:
            mover_asignacion(a, destino)
        self.assertErrorCon(ctx, MSG_DESCANSO)

    def test_mover_respeta_inasistencia(self):
        t = self._trabajador()
        malla = self._malla(_dia(0))
        a = self._asignacion(self._turno(malla, self.primero), t)
        self._inasistencia(t, _dia(1))
        with self.assertRaises(ValidationError) as ctx:
            mover_asignacion(a, self._turno(malla, self.tercero))
        self.assertErrorCon(ctx, MSG_INASISTENCIA)

    def test_mover_a_otra_malla_rechazado(self):
        a = self._asignacion(self._turno(self._malla(_dia(0)), self.primero), self._trabajador())
        otra = self._turno(self._malla(_dia(1)), self.primero)
        with self.assertRaises(ValidationError):
            mover_asignacion(a, otra)


class AutocompletarTests(_BaseMalla, TestCase):
    def setUp(self):
        self._preparar()
        self.malla = self._malla(_dia(0))
        self.turnos = [self._turno(self.malla, b, cupos=2) for b in (self.primero, self.segundo, self.tercero)]

    def _por_turno(self):
        return [self._activas(id_turno=t).count() for t in self.turnos]

    def _turnos_por_trabajador(self):
        return Counter(self._activas(id_turno__id_malla=self.malla).values_list('id_usuario', flat=True))

    def test_reparte_entre_los_tres_bloques(self):
        for _ in range(6):
            self._trabajador()
        autocompletar_malla(self.malla)
        self.assertEqual(self._por_turno(), [2, 2, 2])
        self.assertTrue(all(n == 1 for n in self._turnos_por_trabajador().values()))

    def test_pool_insuficiente_nadie_dobla_turno_el_mismo_dia(self):
        for _ in range(3):
            self._trabajador()
        autocompletar_malla(self.malla)
        por_trabajador = self._turnos_por_trabajador()
        self.assertEqual(len(por_trabajador), 3)
        self.assertTrue(all(n == 1 for n in por_trabajador.values()))
        # Cada bloque recibe uno y quedan cupos pendientes.
        self.assertEqual(self._por_turno(), [1, 1, 1])

    def test_no_supera_el_cupo_objetivo(self):
        for _ in range(10):
            self._trabajador()
        creadas = autocompletar_malla(self.malla)
        self.assertEqual(len(creadas), 6)
        self.assertEqual(self._por_turno(), [2, 2, 2])

    def test_respeta_noches_del_contrato(self):
        bono = self._trabajador(self.bono)
        self._asignacion(self._turno(self._malla(_dia(-1)), self.tercero), bono)
        malla = self._malla(_dia(0), publicada=False)
        Turno.objects.filter(id_malla=malla).delete()
        noche = self._turno(malla, self.tercero, cupos=1)
        autocompletar_malla(malla)
        self.assertFalse(self._activas(id_turno=noche, id_usuario=bono).exists())

    def test_en_malla_publicada_crea_confirmadas(self):
        self.malla.estado = Malla.Estados.PUBLICADA
        self.malla.save()
        self._trabajador()
        creadas = autocompletar_malla(self.malla)
        self.assertEqual(len(creadas), 1)
        self.assertEqual(creadas[0].estado, Asignacion.Estados.CONFIRMADO)


class PublicarTests(_BaseMalla, TestCase):
    def setUp(self):
        self._preparar()

    def test_publicar_confirma_borradores_y_no_toca_reemplazados(self):
        malla = self._malla(_dia(0))
        turno = self._turno(malla, self.primero)
        borrador = self._asignacion(turno, self._trabajador())
        reemplazada = self._asignacion(turno, self._trabajador(), Asignacion.Estados.REEMPLAZADO)

        publicar_malla(malla)

        borrador.refresh_from_db()
        reemplazada.refresh_from_db()
        malla.refresh_from_db()
        self.assertEqual(malla.estado, Malla.Estados.PUBLICADA)
        self.assertEqual(borrador.estado, Asignacion.Estados.CONFIRMADO)
        self.assertEqual(reemplazada.estado, Asignacion.Estados.REEMPLAZADO)

    def test_publicar_dos_veces_rechazado(self):
        malla = self._malla(_dia(0))
        publicar_malla(malla)
        with self.assertRaises(ValidationError):
            publicar_malla(malla)


class MallaApiTests(_BaseMalla, APITestCase):
    def setUp(self):
        self._preparar()
        self.encargado = Usuario.objects.create_user(
            'encargado-cu7@test.cl', _rut_valido(), 'Ana', 'Planificadora', 'clave-segura-123',
            id_rol=Rol.objects.get(pk=Roles.PLANIFICADOR),
        )
        self.client.force_authenticate(self.encargado)

    def _con_licencia(self, usuario, tipo, vence):
        UsuarioLicencia.objects.create(
            id_usuario=usuario, id_tipo_licencia=tipo, especialidades='prueba',
            fecha_emision=date(2025, 1, 1), fecha_vencimiento=vence,
        )
        return usuario

    def test_candidatos_incluye_no_asignables_con_motivo(self):
        tipo = TipoLicencia.objects.create(nombre_licencia='Lic CU-7', descripcion='prueba')
        vigente = _dia(365)
        malla = self._malla(_dia(1))
        turno = self._turno(malla, self.tercero, id_tipo_licencia_req=tipo)

        apto = self._con_licencia(self._trabajador(), tipo, vigente)
        sin_descanso = self._con_licencia(self._trabajador(), tipo, vigente)
        self._asignacion(self._turno(malla, self.segundo), sin_descanso)
        con_inasistencia = self._con_licencia(self._trabajador(), tipo, vigente)
        self._inasistencia(con_inasistencia, _dia(1))
        sin_noches = self._con_licencia(self._trabajador(self.bono), tipo, vigente)
        self._asignacion(self._turno(self._malla(_dia(0)), self.tercero), sin_noches)
        licencia_vencida = self._con_licencia(self._trabajador(), tipo, _dia(-30))
        sin_puesto = self._con_licencia(self._trabajador(con_puesto=False), tipo, vigente)
        ya_asignado = self._con_licencia(self._trabajador(), tipo, vigente)
        self._asignacion(turno, ya_asignado)

        resp = self.client.get(f'/api/turnos/{turno.pk}/candidatos/')
        self.assertEqual(resp.status_code, 200)
        por_id = {c['id_usuario']: c for c in resp.data}

        self.assertNotIn(sin_puesto.pk, por_id)
        self.assertNotIn(ya_asignado.pk, por_id)
        self.assertTrue(por_id[apto.pk]['asignable'])
        self.assertEqual(por_id[apto.pk]['motivos'], [])
        self.assertEqual(resp.data[0]['id_usuario'], apto.pk)

        esperados = {
            sin_descanso.pk: MSG_DESCANSO,
            con_inasistencia.pk: MSG_INASISTENCIA,
            sin_noches.pk: MSG_CONSECUTIVAS,
            licencia_vencida.pk: MSG_LICENCIA,
        }
        for id_usuario, fragmento in esperados.items():
            with self.subTest(fragmento=fragmento):
                candidato = por_id[id_usuario]
                self.assertFalse(candidato['asignable'])
                self.assertTrue(any(fragmento in m for m in candidato['motivos']), candidato['motivos'])

    def test_mover_por_api(self):
        malla = self._malla(_dia(0), publicada=True)
        origen = self._turno(malla, self.primero)
        destino = self._turno(malla, self.tercero)
        a = self._asignacion(origen, self._trabajador(), Asignacion.Estados.CONFIRMADO)

        resp = self.client.post(f'/api/asignaciones/{a.pk}/mover/', {'id_turno': destino.pk}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['id_turno'], destino.pk)
        self.assertEqual(resp.data['estado'], Asignacion.Estados.CONFIRMADO)

        otra = self._turno(self._malla(_dia(3)), self.primero)
        resp = self.client.post(
            f"/api/asignaciones/{resp.data['id_asignacion']}/mover/", {'id_turno': otra.pk}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_quitar_por_api_en_publicada_responde_204(self):
        turno = self._turno(self._malla(_dia(0), publicada=True), self.primero)
        a = self._asignacion(turno, self._trabajador(), Asignacion.Estados.CONFIRMADO)
        resp = self.client.delete(f'/api/asignaciones/{a.pk}/')
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.estado, Asignacion.Estados.REEMPLAZADO)

    def test_trabajador_no_puede_planificar(self):
        turno = self._turno(self._malla(_dia(0)), self.primero)
        trabajador = self._trabajador()
        a = self._asignacion(turno, trabajador)
        self.client.force_authenticate(trabajador)
        self.assertEqual(self.client.get(f'/api/turnos/{turno.pk}/candidatos/').status_code, 403)
        resp = self.client.post(f'/api/asignaciones/{a.pk}/mover/', {'id_turno': turno.pk}, format='json')
        self.assertEqual(resp.status_code, 403)
