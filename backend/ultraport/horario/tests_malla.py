"""CU-7: edición de mallas publicadas, cupos como referencia, mover, candidatos y autocompletar."""
from collections import Counter
from datetime import date, timedelta
from itertools import count

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from usuarios.models import (
    Contrato, Puesto, Rol, TipoLicencia, Usuario, UsuarioLicencia, UsuarioPuesto,
)
from usuarios.permissions import Roles
from usuarios.tests import contrato_de_tipo
from usuarios.validar_rut import calcular_digito_verificador
from .models import Asignacion, BloqueTurno, Malla, NotificacionInasistencia, Turno
from .plantillas import PLANTILLA_BASE
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
        # Quien ejecuta las acciones (queda como actor en la auditoría).
        self.actor = Usuario.objects.create_user(
            f'actor-{next(_apellidos)}@test.cl', _rut_valido(), 'Ana', 'Encargada',
            id_rol=Rol.objects.get(pk=Roles.PLANIFICADOR),
        )
        self.eventual = self._contrato('eventual', semana=None, consecutivas=None)
        self.bono = self._contrato('bono_turno', semana=2, consecutivas=1, extra=False)

    def _contrato(self, tipo, semana, consecutivas, extra=True):
        return contrato_de_tipo(
            tipo, permite_horas_extra=extra,
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
        asignacion = asignar_usuario(turno, self._trabajador(), actor=self.actor)
        self.assertEqual(asignacion.estado, Asignacion.Estados.CONFIRMADO)

    def test_asignar_en_borrador_queda_borrador(self):
        turno = self._turno(self._malla(_dia(0)), self.primero)
        asignacion = asignar_usuario(turno, self._trabajador(), actor=self.actor)
        self.assertEqual(asignacion.estado, Asignacion.Estados.BORRADOR)

    def test_asignar_sobre_el_cupo_se_permite(self):
        turno = self._turno(self._malla(_dia(0)), self.primero, cupos=1)
        asignar_usuario(turno, self._trabajador(), actor=self.actor)
        asignar_usuario(turno, self._trabajador(), actor=self.actor)
        self.assertEqual(self._activas(id_turno=turno).count(), 2)

    def test_asignar_sigue_validando_descanso(self):
        t = self._trabajador()
        self._asignacion(self._turno(self._malla(_dia(0)), self.tercero), t)
        turno = self._turno(self._malla(_dia(1)), self.primero)
        with self.assertRaises(ValidationError) as ctx:
            asignar_usuario(turno, t, actor=self.actor)
        self.assertErrorCon(ctx, MSG_DESCANSO)

    def test_quitar_en_borrador_elimina(self):
        turno = self._turno(self._malla(_dia(0)), self.primero)
        a = self._asignacion(turno, self._trabajador())
        quitar_asignacion(a, actor=self.actor)
        self.assertFalse(Asignacion.objects.filter(pk=a.pk).exists())

    def test_quitar_en_publicada_queda_reemplazado_y_sale_de_la_grilla(self):
        turno = self._turno(self._malla(_dia(0), publicada=True), self.primero)
        a = self._asignacion(turno, self._trabajador(), Asignacion.Estados.CONFIRMADO)
        quitar_asignacion(a, actor=self.actor)
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

        nueva = mover_asignacion(a, destino, actor=self.actor)

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

        resultado = mover_asignacion(a, destino, actor=self.actor)

        self.assertEqual(resultado.pk, a.pk)
        self.assertEqual(resultado.id_turno, destino)
        self.assertEqual(Asignacion.objects.count(), 1)

    def test_mover_primero_a_segundo_mismo_dia_excluye_el_origen(self):
        # Sin excluir el origen habría 0 h de descanso entre 15:30 y 15:30.
        malla = self._malla(_dia(0))
        origen = self._turno(malla, self.primero)
        destino = self._turno(malla, self.segundo)
        a = self._asignacion(origen, self._trabajador())
        self.assertEqual(mover_asignacion(a, destino, actor=self.actor).id_turno, destino)

    def test_mover_respeta_descanso(self):
        t = self._trabajador()
        self._asignacion(self._turno(self._malla(_dia(-1)), self.tercero), t)
        malla = self._malla(_dia(0))
        a = self._asignacion(self._turno(malla, self.segundo), t)
        destino = self._turno(malla, self.primero)
        with self.assertRaises(ValidationError) as ctx:
            mover_asignacion(a, destino, actor=self.actor)
        self.assertErrorCon(ctx, MSG_DESCANSO)

    def test_mover_respeta_inasistencia(self):
        t = self._trabajador()
        malla = self._malla(_dia(0))
        a = self._asignacion(self._turno(malla, self.primero), t)
        self._inasistencia(t, _dia(1))
        with self.assertRaises(ValidationError) as ctx:
            mover_asignacion(a, self._turno(malla, self.tercero), actor=self.actor)
        self.assertErrorCon(ctx, MSG_INASISTENCIA)

    def test_mover_a_otra_malla_rechazado(self):
        a = self._asignacion(self._turno(self._malla(_dia(0)), self.primero), self._trabajador())
        otra = self._turno(self._malla(_dia(1)), self.primero)
        with self.assertRaises(ValidationError):
            mover_asignacion(a, otra, actor=self.actor)


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
        autocompletar_malla(self.malla, actor=self.actor)
        self.assertEqual(self._por_turno(), [2, 2, 2])
        self.assertTrue(all(n == 1 for n in self._turnos_por_trabajador().values()))

    def test_pool_insuficiente_nadie_dobla_turno_el_mismo_dia(self):
        for _ in range(3):
            self._trabajador()
        autocompletar_malla(self.malla, actor=self.actor)
        por_trabajador = self._turnos_por_trabajador()
        self.assertEqual(len(por_trabajador), 3)
        self.assertTrue(all(n == 1 for n in por_trabajador.values()))
        # Cada bloque recibe uno y quedan cupos pendientes.
        self.assertEqual(self._por_turno(), [1, 1, 1])

    def test_no_supera_el_cupo_objetivo(self):
        for _ in range(10):
            self._trabajador()
        creadas = autocompletar_malla(self.malla, actor=self.actor)
        self.assertEqual(len(creadas), 6)
        self.assertEqual(self._por_turno(), [2, 2, 2])

    def test_respeta_noches_del_contrato(self):
        bono = self._trabajador(self.bono)
        self._asignacion(self._turno(self._malla(_dia(-1)), self.tercero), bono)
        malla = self._malla(_dia(0), publicada=False)
        Turno.objects.filter(id_malla=malla).delete()
        noche = self._turno(malla, self.tercero, cupos=1)
        autocompletar_malla(malla, actor=self.actor)
        self.assertFalse(self._activas(id_turno=noche, id_usuario=bono).exists())

    def test_en_malla_publicada_crea_confirmadas(self):
        self.malla.estado = Malla.Estados.PUBLICADA
        self.malla.save()
        self._trabajador()
        creadas = autocompletar_malla(self.malla, actor=self.actor)
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

        publicar_malla(malla, actor=self.actor)

        borrador.refresh_from_db()
        reemplazada.refresh_from_db()
        malla.refresh_from_db()
        self.assertEqual(malla.estado, Malla.Estados.PUBLICADA)
        self.assertEqual(borrador.estado, Asignacion.Estados.CONFIRMADO)
        self.assertEqual(reemplazada.estado, Asignacion.Estados.REEMPLAZADO)

    def test_publicar_dos_veces_rechazado(self):
        malla = self._malla(_dia(0))
        publicar_malla(malla, actor=self.actor)
        with self.assertRaises(ValidationError):
            publicar_malla(malla, actor=self.actor)


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


class IniciarPlantillaApiTests(_BaseMalla, APITestCase):
    """RF-16: iniciar la malla del día desde la plantilla y elegir turno."""

    URL = '/api/mallas/iniciar-plantilla/'

    def setUp(self):
        self._preparar()
        self.encargado = Usuario.objects.create_user(
            'encargado-rf16@test.cl', _rut_valido(), 'Ana', 'Planificadora', 'clave-segura-123',
            id_rol=Rol.objects.get(pk=Roles.PLANIFICADOR),
        )
        self.client.force_authenticate(self.encargado)
        self.futura = timezone.localdate() + timedelta(days=30)

    def _iniciar(self, fecha=None):
        return self.client.post(self.URL, {'fecha': fecha.isoformat()} if fecha else {}, format='json')

    def test_crea_la_malla_con_los_tres_bloques(self):
        resp = self._iniciar(self.futura)
        self.assertEqual(resp.status_code, 201)
        malla = Malla.objects.get(pk=resp.data['id_malla'])
        self.assertEqual(malla.fecha, self.futura)
        por_bloque = Counter(malla.turnos.values_list('id_bloque__orden_secuencia', flat=True))
        self.assertEqual(set(por_bloque), {1, 2, 3})
        for orden in (1, 2, 3):
            self.assertEqual(por_bloque[orden], len(PLANTILLA_BASE))
        ordenes_api = {t['bloque']['orden_secuencia'] for t in resp.data['turnos']}
        self.assertEqual(ordenes_api, {1, 2, 3})

    def test_fecha_con_malla_existente_devuelve_la_misma_sin_duplicar(self):
        primera = self._iniciar(self.futura)
        turnos_antes = Turno.objects.count()

        segunda = self._iniciar(self.futura)

        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(segunda.data['id_malla'], primera.data['id_malla'])
        self.assertEqual(Malla.objects.filter(fecha=self.futura).count(), 1)
        self.assertEqual(Turno.objects.count(), turnos_antes)
        self.assertEqual(len(segunda.data['turnos']), len(primera.data['turnos']))

    def test_malla_existente_de_hoy_se_abre_aunque_no_sea_futura(self):
        hoy = timezone.localdate()
        existente = self._malla(hoy, publicada=True)
        self._turno(existente, self.primero)

        resp = self._iniciar(hoy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['id_malla'], existente.pk)
        self.assertEqual(resp.data['estado'], Malla.Estados.PUBLICADA)

    def test_fecha_pasada_sin_malla_sigue_rechazada(self):
        resp = self._iniciar(timezone.localdate() - timedelta(days=1))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Malla.objects.exists())

    def test_sin_fecha_usa_manana(self):
        resp = self._iniciar()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['fecha'], (timezone.localdate() + timedelta(days=1)).isoformat())

    def test_fecha_invalida_400_y_no_500(self):
        resp = self.client.post(self.URL, {'fecha': '2026-13-45'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fecha', resp.data)

    def test_trabajador_no_puede_iniciar(self):
        self.client.force_authenticate(self._trabajador())
        self.assertEqual(self._iniciar(self.futura).status_code, 403)

    def test_catalogo_de_bloques_con_horarios_en_orden(self):
        resp = self.client.get('/api/bloques/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([b['orden_secuencia'] for b in resp.data], [1, 2, 3])
        for b in resp.data:
            self.assertTrue(b['hora_inicio'])
            self.assertTrue(b['hora_termino'])
        self.client.force_authenticate(self._trabajador())
        self.assertEqual(self.client.get('/api/bloques/').status_code, 403)
