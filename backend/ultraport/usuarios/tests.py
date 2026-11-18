from datetime import date
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase, override_settings

from rest_framework.test import APITestCase

from .models import Contrato, Rol, Usuario
from .permissions import Roles
from .serializers import MENSAJE_CREDENCIALES_INVALIDAS
from .services import construir_enlace_recuperacion, enviar_correo_recuperacion
from .validar_rut import calcular_digito_verificador
from .views import MENSAJE_GENERICO

LOGIN_URL = '/api/login/'
RECUPERAR_URL = '/api/recuperar-password/'
USUARIOS_URL = '/api/usuarios/'
PASSWORD = 'clave-segura-123'


def crear_usuario(correo, rut, rol=Roles.TRABAJADOR, **extra):
    return Usuario.objects.create_user(
        correo, rut, 'Juan', 'Pérez', PASSWORD, id_rol=Rol.objects.get(pk=rol), **extra)


class LoginTests(APITestCase):
    """RF-01, RF-02 y RF-04."""

    def setUp(self):
        self.usuario = crear_usuario('trabajador@test.cl', '11111111-1')

    def _login(self, identificador, password=PASSWORD):
        return self.client.post(
            LOGIN_URL, {'identificador': identificador, 'password': password}, format='json')

    def test_login_con_correo_entrega_tokens_y_usuario(self):
        resp = self._login('trabajador@test.cl')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)
        self.assertEqual(resp.data['usuario']['rut'], '11111111-1')
        self.assertEqual(resp.data['usuario']['id_rol'], Roles.TRABAJADOR)

    def test_login_correo_no_distingue_mayusculas(self):
        self.assertEqual(self._login('Trabajador@Test.CL').status_code, 200)

    def test_login_con_rut_en_distintos_formatos(self):
        for rut in ('11111111-1', '11.111.111-1', '111111111', ' 11.111.111-1 '):
            with self.subTest(rut=rut):
                resp = self._login(rut)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.data['usuario']['correo'], 'trabajador@test.cl')

    def test_login_con_rut_dv_k_en_minuscula(self):
        crear_usuario('k@test.cl', '10000013-K')
        resp = self._login('10.000.013-k')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['usuario']['correo'], 'k@test.cl')

    def test_login_encuentra_rut_guardado_con_puntos(self):
        usuario = crear_usuario('puntos@test.cl', '12345678-5')
        Usuario.objects.filter(pk=usuario.pk).update(rut='12.345.678-5')
        for rut in ('12345678-5', '12.345.678-5'):
            with self.subTest(rut=rut):
                resp = self._login(rut)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.data['usuario']['correo'], 'puntos@test.cl')

    def test_texto_del_mensaje_de_rechazo(self):
        # El frontend muestra este texto tal cual; cambiarlo debe ser deliberado.
        self.assertEqual(MENSAJE_CREDENCIALES_INVALIDAS, 'RUT, correo o contraseña incorrectos')
        resp = self._login('trabajador@test.cl', 'otra-clave-999')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data['detail'], 'RUT, correo o contraseña incorrectos')

    def test_rechazos_responden_igual(self):
        crear_usuario('inactivo@test.cl', '22222222-2', estado='inactivo')
        crear_usuario('desactivado@test.cl', '33333333-3', is_active=False)
        casos = {
            'password incorrecta (correo)': self._login('trabajador@test.cl', 'otra-clave-999'),
            'password incorrecta (rut)': self._login('11.111.111-1', 'otra-clave-999'),
            'correo inexistente': self._login('nadie@test.cl'),
            'rut inexistente': self._login('44444444-4'),
            'rut mal formado': self._login('x'),
            'estado inactivo (correo)': self._login('inactivo@test.cl'),
            'estado inactivo (rut)': self._login('22.222.222-2'),
            'is_active False': self._login('desactivado@test.cl'),
        }
        for caso, resp in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(resp.status_code, 401)
                self.assertEqual(resp.data['detail'], MENSAJE_CREDENCIALES_INVALIDAS)
                self.assertNotIn('access', resp.data)
        self.assertEqual(len({str(resp.data) for resp in casos.values()}), 1)


class NormalizacionRutTests(APITestCase):
    def setUp(self):
        self.planificador = crear_usuario('plan@test.cl', '11111111-1', Roles.PLANIFICADOR)
        self.client.force_authenticate(self.planificador)

    def test_save_normaliza_rut(self):
        usuario = crear_usuario('k@test.cl', '10.000.013-k')
        usuario.refresh_from_db()
        self.assertEqual(usuario.rut, '10000013-K')

    def _crear(self, rut, correo):
        return self.client.post(USUARIOS_URL, {
            'rut': rut, 'nombres': 'Ana', 'apellidos': 'Soto', 'correo': correo,
            'telefono': '912345678', 'id_rol': Roles.TRABAJADOR, 'password': PASSWORD,
        }, format='json')

    def test_api_normaliza_y_detecta_rut_duplicado_en_otro_formato(self):
        resp = self._crear('12.345.678-5', 'ana@test.cl')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['rut'], '12345678-5')
        resp = self._crear('12345678-5', 'otra@test.cl')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('rut', resp.data)

    def test_api_rechaza_rut_invalido(self):
        resp = self._crear('12.345.678-9', 'ana@test.cl')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('rut', resp.data)


class DesactivarUsuarioTests(APITestCase):

    def test_desactivar_bloquea_login(self):
        planificador = crear_usuario('plan@test.cl', '11111111-1', Roles.PLANIFICADOR)
        trabajador = crear_usuario('trabajador@test.cl', '22222222-2')
        self.client.force_authenticate(planificador)
        self.assertEqual(self.client.delete(f'{USUARIOS_URL}{trabajador.pk}/').status_code, 204)
        trabajador.refresh_from_db()
        self.assertEqual(trabajador.estado, 'inactivo')
        self.assertFalse(trabajador.is_active)

        self.client.force_authenticate(None)
        resp = self.client.post(
            LOGIN_URL, {'identificador': '22.222.222-2', 'password': PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data['detail'], MENSAJE_CREDENCIALES_INVALIDAS)

    def test_reactivar_permite_login_de_nuevo(self):
        planificador = crear_usuario('plan@test.cl', '11111111-1', Roles.PLANIFICADOR)
        trabajador = crear_usuario('trabajador@test.cl', '22222222-2')
        url = f'{USUARIOS_URL}{trabajador.pk}/'
        self.client.force_authenticate(planificador)

        self.assertEqual(self.client.delete(url).status_code, 204)
        resp = self.client.patch(url, {'estado': 'activo'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        trabajador.refresh_from_db()
        self.assertEqual(trabajador.estado, 'activo')
        self.assertTrue(trabajador.is_active)

        self.client.force_authenticate(None)
        resp = self.client.post(
            LOGIN_URL, {'identificador': '22.222.222-2', 'password': PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_editar_a_inactivo_desactiva(self):
        planificador = crear_usuario('plan@test.cl', '11111111-1', Roles.PLANIFICADOR)
        trabajador = crear_usuario('trabajador@test.cl', '22222222-2')
        self.client.force_authenticate(planificador)
        resp = self.client.patch(
            f'{USUARIOS_URL}{trabajador.pk}/', {'estado': 'inactivo'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        trabajador.refresh_from_db()
        self.assertFalse(trabajador.is_active)


@patch('usuarios.views.enviar_correo_recuperacion')
class SolicitarRecuperacionTests(APITestCase):

    def setUp(self):
        self.usuario = crear_usuario('trabajador@test.cl', '11111111-1')

    def _solicitar(self, identificador):
        return self.client.post(RECUPERAR_URL, {'identificador': identificador}, format='json')

    def test_envia_correo_con_correo_o_rut(self, enviar):
        for identificador in ('trabajador@test.cl', '11.111.111-1', '11111111-1'):
            with self.subTest(identificador=identificador):
                enviar.reset_mock()
                resp = self._solicitar(identificador)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.data, {'mensaje': MENSAJE_GENERICO})
                enviar.assert_called_once()
                self.assertEqual(enviar.call_args.args[0], self.usuario)

    def test_misma_respuesta_exista_o_no_la_cuenta(self, enviar):
        crear_usuario('inactivo@test.cl', '22222222-2', estado='inactivo')
        crear_usuario('desactivado@test.cl', '33333333-3', is_active=False)
        existente = self._solicitar('trabajador@test.cl')
        enviar.reset_mock()
        for identificador in ('nadie@test.cl', '44444444-4', 'x', 'inactivo@test.cl', '33333333-3'):
            with self.subTest(identificador=identificador):
                resp = self._solicitar(identificador)
                self.assertEqual(resp.status_code, existente.status_code)
                self.assertEqual(resp.data, existente.data)
        enviar.assert_not_called()

    def test_fallo_de_envio_no_cambia_la_respuesta(self, enviar):
        enviar.side_effect = RuntimeError('Resend caído')
        with self.assertLogs('usuarios.views', level='ERROR'):
            resp = self._solicitar('trabajador@test.cl')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {'mensaje': MENSAJE_GENERICO})

    def test_identificador_obligatorio(self, enviar):
        resp = self.client.post(RECUPERAR_URL, {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('identificador', resp.data)
        enviar.assert_not_called()


class ListadoUsuariosTests(APITestCase):
    def setUp(self):
        contrato = Contrato.objects.create(
            tipo='cppt', turno_habitual='rotativo', horas_semanales_pactadas=45,
            fecha_inicio=date(2026, 1, 1))
        self.planificador = crear_usuario('plan@test.cl', '11111111-1', Roles.PLANIFICADOR)
        self.con_contrato = crear_usuario('cppt@test.cl', '22222222-2', id_contrato=contrato)
        self.sin_contrato = crear_usuario('sin@test.cl', '33333333-3')

    def test_listado_incluye_tipo_contrato(self):
        self.client.force_authenticate(self.planificador)
        resp = self.client.get(USUARIOS_URL)
        self.assertEqual(resp.status_code, 200)
        por_correo = {u['correo']: u for u in resp.data['results']}
        self.assertEqual(por_correo['cppt@test.cl']['tipo_contrato'], 'CPPT')
        self.assertIsNone(por_correo['sin@test.cl']['tipo_contrato'])
        self.assertIn('id_contrato', por_correo['cppt@test.cl'])

    def test_tipo_contrato_es_solo_lectura(self):
        self.client.force_authenticate(self.planificador)
        resp = self.client.patch(
            f'{USUARIOS_URL}{self.sin_contrato.pk}/', {'tipo_contrato': 'CPPT'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.sin_contrato.refresh_from_db()
        self.assertIsNone(self.sin_contrato.id_contrato)

    def test_trabajador_no_ve_el_listado(self):
        self.client.force_authenticate(self.con_contrato)
        self.assertEqual(self.client.get(USUARIOS_URL).status_code, 403)


def rut_valido(cuerpo):
    cuerpo = str(cuerpo)
    return f'{cuerpo}-{calcular_digito_verificador(cuerpo)}'


class PaginacionUsuariosTests(APITestCase):
    """Listado paginado (20 por página) con búsqueda por nombre o RUT."""

    TOTAL = 45  # planificador + 44 trabajadores; con Ana son 46: páginas de 20, 20 y 6

    def setUp(self):
        self.planificador = crear_usuario('plan@test.cl', '11111111-1', Roles.PLANIFICADOR)
        rol = Rol.objects.get(pk=Roles.TRABAJADOR)
        for i in range(self.TOTAL - 1):
            # Sin contraseña (no se calcula hash): mucho más rápido.
            Usuario.objects.create_user(
                f'usuario{i:02d}@test.cl', rut_valido(20000000 + i),
                f'Nombre{i:02d}', 'Apellido', id_rol=rol)
        Usuario.objects.create_user(
            'ana@test.cl', '12345678-5', 'Ana María', 'Soto Rojas', id_rol=rol)
        self.client.force_authenticate(self.planificador)

    def _listar(self, **params):
        return self.client.get(USUARIOS_URL, params)

    def test_primera_pagina_trae_20_y_metadatos(self):
        resp = self._listar()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], self.TOTAL + 1)
        self.assertEqual(len(resp.data['results']), 20)
        self.assertEqual(resp.data['pagina'], 1)
        self.assertEqual(resp.data['total_paginas'], 3)
        self.assertIsNone(resp.data['previous'])
        self.assertIsNotNone(resp.data['next'])

    def test_ultima_pagina_y_recorrido_sin_repetidos(self):
        vistos = []
        for pagina in (1, 2, 3):
            resp = self._listar(page=pagina)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data['pagina'], pagina)
            vistos += [u['id_usuario'] for u in resp.data['results']]
        self.assertEqual(len(resp.data['results']), 6)
        self.assertIsNone(resp.data['next'])
        self.assertEqual(len(vistos), self.TOTAL + 1)
        self.assertEqual(len(set(vistos)), self.TOTAL + 1)

    def test_pagina_fuera_de_rango_es_404(self):
        self.assertEqual(self._listar(page=4).status_code, 404)

    def test_busqueda_por_nombre_parcial_y_completo(self):
        for termino in ('ana', 'ANA MARÍA', 'ana maría soto', 'rojas'):
            with self.subTest(termino=termino):
                resp = self._listar(search=termino)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.data['count'], 1)
                self.assertEqual(resp.data['results'][0]['correo'], 'ana@test.cl')

    def test_busqueda_por_rut_con_o_sin_puntos(self):
        for termino in ('12345678-5', '12.345.678-5', '12.345', '345678'):
            with self.subTest(termino=termino):
                resp = self._listar(search=termino)
                self.assertEqual(resp.data['count'], 1)
                self.assertEqual(resp.data['results'][0]['rut'], '12345678-5')

    def test_busqueda_se_pagina(self):
        # 'Nombre' coincide con los 44 trabajadores generados.
        resp = self._listar(search='nombre')
        self.assertEqual(resp.data['count'], self.TOTAL - 1)
        self.assertEqual(resp.data['total_paginas'], 3)
        self.assertEqual(len(resp.data['results']), 20)
        resp = self._listar(search='nombre', page=3)
        self.assertEqual(len(resp.data['results']), 4)
        self.assertTrue(all('Nombre' in u['nombres'] for u in resp.data['results']))

    def test_busqueda_sin_resultados(self):
        resp = self._listar(search='no-existe-nadie')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 0)
        self.assertEqual(resp.data['results'], [])
        self.assertEqual(resp.data['total_paginas'], 1)

    def test_detalle_no_se_pagina_ni_filtra(self):
        ana = Usuario.objects.get(correo='ana@test.cl')
        resp = self.client.get(f'{USUARIOS_URL}{ana.pk}/', {'search': 'otro'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['correo'], 'ana@test.cl')


class EnlaceRecuperacionTests(SimpleTestCase):
    """El enlace del correo debe apuntar a la ruta /resetear-password del frontend (main.jsx),
    que lee el parámetro ?token= (RestablecerPassword.jsx)."""

    def _partes(self, enlace):
        partes = urlsplit(enlace)
        return partes, parse_qs(partes.query)

    @override_settings(FRONTEND_URL='http://localhost:5173')
    def test_enlace_usa_frontend_url_ruta_y_token(self):
        partes, query = self._partes(construir_enlace_recuperacion('abc-123_XYZ'))
        self.assertEqual(f'{partes.scheme}://{partes.netloc}', 'http://localhost:5173')
        self.assertEqual(partes.path, '/resetear-password')
        self.assertEqual(query, {'token': ['abc-123_XYZ']})

    @override_settings(FRONTEND_URL='https://ultraport.example.com/')
    def test_barra_final_en_frontend_url_no_duplica_slash(self):
        enlace = construir_enlace_recuperacion('tok')
        self.assertEqual(enlace, 'https://ultraport.example.com/resetear-password?token=tok')

    @override_settings(FRONTEND_URL='http://localhost:5173', EMAIL_FROM='no-reply@test.cl')
    @patch('usuarios.services.resend.Emails.send')
    def test_correo_incluye_el_enlace(self, mock_send):
        usuario = Usuario(correo='ana@test.cl', nombres='Ana')
        token = 'tok-correo'
        enviar_correo_recuperacion(usuario, token)
        html = mock_send.call_args.args[0]['html']
        self.assertIn(f'href="{construir_enlace_recuperacion(token)}"', html)
