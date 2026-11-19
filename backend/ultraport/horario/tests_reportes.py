"""RF-19 (malla exportable), RF-20 (filtro por fechas) y RF-21 (reporte de ausencias).

PDF y Excel. Para buscar texto en el PDF se desactiva la compresión de
ReportLab (las celdas quedan como texto plano en el flujo de la página).
"""
from datetime import date
from io import BytesIO
from itertools import count
from unittest import mock

from openpyxl import load_workbook
from rest_framework.test import APITestCase

from usuarios.models import Contrato, Puesto, Rol, Usuario
from usuarios.permissions import Roles
from usuarios.validar_rut import calcular_digito_verificador
from .models import Area, Asignacion, BloqueTurno, Malla, NotificacionInasistencia, Turno
from .reportes import CONTENT_TYPE_PDF, CONTENT_TYPE_XLSX

FECHA = date(2026, 11, 20)
_ruts = count(80000000)


def _rut():
    cuerpo = str(next(_ruts))
    return f'{cuerpo}-{calcular_digito_verificador(cuerpo)}'


def _sin_compresion():
    return mock.patch('reportlab.rl_config.pageCompression', 0)


def _textos_xlsx(resp):
    hoja = load_workbook(BytesIO(resp.content)).active
    return [
        '' if v is None else str(v)
        for fila in hoja.iter_rows(values_only=True) for v in fila
    ]


def _encabezado_xlsx(resp):
    hoja = load_workbook(BytesIO(resp.content)).active
    return [c for c in next(hoja.iter_rows(min_row=4, max_row=4, values_only=True)) if c]


class _BaseReportes(APITestCase):
    def setUp(self):
        self.contrato = Contrato.objects.create(
            tipo='eventual', turno_habitual='rotativo', horas_semanales_pactadas=42,
            fecha_inicio=date(2026, 1, 1),
        )
        self.admin = self._usuario(Roles.ADMINISTRADOR, 'admin', 'Ada', 'Admin')
        self.encargado = self._usuario(Roles.PLANIFICADOR, 'encargado', 'Ana', 'Planificadora')
        self.trabajador = self._usuario(Roles.TRABAJADOR, 'yo', 'Juan', 'Pérez')
        self.companero = self._usuario(Roles.TRABAJADOR, 'companero', 'Carla', 'Muñoz')

    def _usuario(self, rol, alias, nombres, apellidos):
        return Usuario.objects.create_user(
            f'{alias}@reportes.cl', _rut(), nombres, apellidos, 'clave-segura-123',
            id_rol=Rol.objects.get(pk=rol), id_contrato=self.contrato,
        )

    def _get(self, usuario, url, **params):
        self.client.force_authenticate(usuario)
        return self.client.get(url, params)


class ReporteMallaTests(_BaseReportes):
    """RF-19 y privacidad de la exportación descargable por un trabajador."""

    def setUp(self):
        super().setUp()
        self.malla = Malla.objects.create(fecha=FECHA, estado=Malla.Estados.PUBLICADA)
        area = Area.objects.create(nombre_area='Muelle reportes')
        puesto = Puesto.objects.create(nombre_puesto='Operador reportes')
        primero = BloqueTurno.objects.get(orden_secuencia=1)
        tercero = BloqueTurno.objects.get(orden_secuencia=3)
        turno = Turno.objects.create(
            id_malla=self.malla, id_area=area, id_bloque=primero, id_puesto=puesto, cupos=2)
        turno_noche = Turno.objects.create(
            id_malla=self.malla, id_area=area, id_bloque=tercero, id_puesto=puesto, cupos=1)
        for usuario in (self.trabajador, self.companero):
            Asignacion.objects.create(
                id_turno=turno, id_usuario=usuario, estado=Asignacion.Estados.CONFIRMADO)
        self.nocturno = self._usuario(Roles.TRABAJADOR, 'nocturno', 'Pedro', 'Nocturno')
        Asignacion.objects.create(
            id_turno=turno_noche, id_usuario=self.nocturno, estado=Asignacion.Estados.CONFIRMADO)

    def _url(self, formato, pk=None):
        return f'/api/reportes/malla/{pk or self.malla.pk}/{formato}/'

    def test_pdf_responde_200_con_content_type_pdf(self):
        resp = self._get(self.encargado, self._url('pdf'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], CONTENT_TYPE_PDF)
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertIn('.pdf', resp['Content-Disposition'])

    def test_xlsx_responde_200_con_content_type_xlsx(self):
        resp = self._get(self.encargado, self._url('xlsx'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], CONTENT_TYPE_XLSX)
        self.assertIn('.xlsx', resp['Content-Disposition'])

    def test_xlsx_incluye_nombre_rut_y_correo_para_encargado(self):
        textos = _textos_xlsx(self._get(self.encargado, self._url('xlsx')))
        for u in (self.trabajador, self.companero):
            self.assertIn(f'{u.nombres} {u.apellidos}', textos)
            self.assertIn(u.rut, textos)
            self.assertIn(u.correo, textos)

    def test_pdf_incluye_nombre_rut_y_correo_para_encargado(self):
        with _sin_compresion():
            contenido = self._get(self.encargado, self._url('pdf')).content
        self.assertIn(self.companero.rut.encode(), contenido)
        self.assertIn(self.companero.correo.encode(), contenido)
        self.assertIn(b'Carla', contenido)

    def test_pdf_ya_no_muestra_columna_id_usuario(self):
        with _sin_compresion():
            contenido = self._get(self.encargado, self._url('pdf')).content
        self.assertNotIn(b'ID usuario', contenido)

    def test_trabajador_xlsx_sin_rut_ni_correo_ajenos(self):
        resp = self._get(self.trabajador, self._url('xlsx'))
        self.assertEqual(resp.status_code, 200)
        textos = _textos_xlsx(resp)
        self.assertIn('Carla Muñoz', textos)
        for u in (self.companero, self.nocturno):
            self.assertNotIn(u.rut, textos)
            self.assertNotIn(u.correo, textos)
        encabezado = _encabezado_xlsx(resp)
        self.assertNotIn('RUT', encabezado)
        self.assertNotIn('Correo', encabezado)
        for columna in ('Código', 'Nombre', 'Función', 'Máquina'):
            self.assertIn(columna, encabezado)

    def test_trabajador_pdf_sin_rut_ni_correo_ajenos(self):
        with _sin_compresion():
            resp = self._get(self.trabajador, self._url('pdf'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Carla', resp.content)
        for u in (self.companero, self.nocturno):
            self.assertNotIn(u.rut.encode(), resp.content)
            self.assertNotIn(u.correo.encode(), resp.content)

    def test_administrador_recibe_200_no_403(self):
        for formato, content_type in (('pdf', CONTENT_TYPE_PDF), ('xlsx', CONTENT_TYPE_XLSX)):
            with self.subTest(formato=formato):
                resp = self._get(self.admin, self._url(formato))
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp['Content-Type'], content_type)

    def test_administrador_recibe_rut_y_correo(self):
        textos = _textos_xlsx(self._get(self.admin, self._url('xlsx')))
        self.assertIn(self.companero.rut, textos)
        self.assertIn(self.companero.correo, textos)

    def test_filtro_por_bloque_igual_en_xlsx(self):
        textos = _textos_xlsx(self._get(self.encargado, self._url('xlsx'), bloque='primer_turno'))
        self.assertIn('Carla Muñoz', textos)
        self.assertNotIn('Pedro Nocturno', textos)

    def test_malla_borrador_no_se_exporta(self):
        borrador = Malla.objects.create(fecha=date(2026, 11, 21))
        for formato in ('pdf', 'xlsx'):
            with self.subTest(formato=formato):
                resp = self._get(self.encargado, self._url(formato, borrador.pk))
                self.assertEqual(resp.status_code, 400)

    def test_listado_de_mallas_publicadas_para_admin_sin_planificar(self):
        Malla.objects.create(fecha=date(2026, 11, 21))  # borrador: no se lista
        resp = self._get(self.admin, '/api/reportes/mallas/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([m['id_malla'] for m in resp.data], [self.malla.pk])
        # El administrador sigue sin poder planificar.
        self.assertEqual(self._get(self.admin, '/api/mallas/').status_code, 403)


class ReporteInasistenciasTests(_BaseReportes):
    """RF-20 (rango de fechas) y RF-21 (reporte descargable)."""

    URL_PDF = '/api/reportes/inasistencias/pdf/'
    URL_XLSX = '/api/reportes/inasistencias/xlsx/'
    RANGO = {'desde': '2026-11-10', 'hasta': '2026-11-20'}

    def setUp(self):
        super().setUp()
        self._aviso(self.companero, 'Dentro del rango', date(2026, 11, 12), date(2026, 11, 14))
        self._aviso(self.trabajador, 'Cruza el inicio', date(2026, 11, 5), date(2026, 11, 11))
        self._aviso(self.trabajador, 'Un solo dia', date(2026, 11, 20),
                    estado=NotificacionInasistencia.PENDIENTE)
        self._aviso(self.companero, 'Antes del rango', date(2026, 11, 1), date(2026, 11, 9))
        self._aviso(self.companero, 'Despues del rango', date(2026, 11, 21), date(2026, 11, 25))
        self._aviso(self.companero, 'Dia suelto previo', date(2026, 11, 9))

    def _aviso(self, usuario, motivo, inicio, fin=None, estado=NotificacionInasistencia.APROBADO):
        return NotificacionInasistencia.objects.create(
            id_usuario=usuario, motivo=motivo, fecha_inicio=inicio, fecha_fin=fin, estado=estado)

    def test_pdf_responde_200_con_content_type_pdf(self):
        resp = self._get(self.encargado, self.URL_PDF, **self.RANGO)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], CONTENT_TYPE_PDF)
        self.assertTrue(resp.content.startswith(b'%PDF'))

    def test_xlsx_responde_200_con_content_type_xlsx(self):
        resp = self._get(self.encargado, self.URL_XLSX, **self.RANGO)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], CONTENT_TYPE_XLSX)

    def test_xlsx_incluye_nombre_rut_y_correo(self):
        textos = _textos_xlsx(self._get(self.encargado, self.URL_XLSX, **self.RANGO))
        self.assertIn('Carla Muñoz', textos)
        self.assertIn(self.companero.rut, textos)
        self.assertIn(self.companero.correo, textos)
        self.assertNotIn('ID usuario', textos)

    def test_filtro_de_fechas_excluye_fuera_del_rango_xlsx(self):
        textos = _textos_xlsx(self._get(self.encargado, self.URL_XLSX, **self.RANGO))
        for motivo in ('Dentro del rango', 'Cruza el inicio', 'Un solo dia'):
            self.assertIn(motivo, textos)
        for motivo in ('Antes del rango', 'Despues del rango', 'Dia suelto previo'):
            self.assertNotIn(motivo, textos)

    def test_filtro_de_fechas_excluye_fuera_del_rango_pdf(self):
        with _sin_compresion():
            contenido = self._get(self.encargado, self.URL_PDF, **self.RANGO).content
        self.assertIn(b'Dentro del rango', contenido)
        self.assertIn(self.companero.rut.encode(), contenido)
        for motivo in (b'Antes del rango', b'Despues del rango', b'Dia suelto previo'):
            self.assertNotIn(motivo, contenido)

    def test_filtro_por_estado_igual_en_xlsx(self):
        textos = _textos_xlsx(self._get(
            self.encargado, self.URL_XLSX, estado=NotificacionInasistencia.PENDIENTE, **self.RANGO))
        self.assertIn('Un solo dia', textos)
        self.assertNotIn('Dentro del rango', textos)

    def test_rango_invalido_400_en_ambos_formatos(self):
        for url in (self.URL_PDF, self.URL_XLSX):
            with self.subTest(url=url):
                self.assertEqual(self._get(self.encargado, url, desde='2026-11-20', hasta='2026-11-10').status_code, 400)
                self.assertEqual(self._get(self.encargado, url, desde='x').status_code, 400)

    def test_administrador_recibe_200_no_403(self):
        for url, content_type in ((self.URL_PDF, CONTENT_TYPE_PDF), (self.URL_XLSX, CONTENT_TYPE_XLSX)):
            with self.subTest(url=url):
                resp = self._get(self.admin, url, **self.RANGO)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp['Content-Type'], content_type)

    def test_trabajador_no_descarga_inasistencias_ajenas(self):
        for url in (self.URL_PDF, self.URL_XLSX):
            with self.subTest(url=url):
                self.assertEqual(self._get(self.trabajador, url, **self.RANGO).status_code, 403)
