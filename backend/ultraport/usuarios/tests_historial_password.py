from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.hashers import check_password, identify_hasher
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase

from .historial_password import MAX_HISTORIAL_PASSWORD, MENSAJE_PASSWORD_REUTILIZADA
from .models import HistorialPassword, TokenRecuperacion, Usuario
from .permissions import Roles
from .services import crear_token_recuperacion
from .tests import PASSWORD, crear_usuario

RESTABLECER_URL = '/api/restablecer-password/'

# Pasan los validadores de Django (largo, comunes, numéricas, parecido al usuario).
NUEVAS = [f'Muelle-Norte-{n}x' for n in range(1, 8)]


class HistorialPasswordTests(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin@test.cl', '11111111-1', rol=Roles.ADMINISTRADOR)
        self.usuario = crear_usuario('trabajador@test.cl', '22222222-2')

    # --- Flujos ---

    def _restablecer(self, password):
        token = crear_token_recuperacion(self.usuario)
        resp = self.client.post(RESTABLECER_URL, {'token': token, 'password': password}, format='json')
        return resp, token

    def _editar_como_admin(self, password):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(f'/api/usuarios/{self.usuario.pk}/', {'password': password}, format='json')
        self.client.force_authenticate(None)
        return resp

    def _cambiar_varias(self, passwords):
        for password in passwords:
            resp = self._editar_como_admin(password)
            self.assertEqual(resp.status_code, 200, resp.data)

    def _password_actual_es(self, password):
        self.usuario.refresh_from_db()
        return check_password(password, self.usuario.password)

    def assertRechazada(self, resp):
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['password'], [MENSAJE_PASSWORD_REUTILIZADA])

    # --- Rechazos ---

    def test_restablecer_rechaza_la_actual_y_no_consume_el_token(self):
        resp, token = self._restablecer(PASSWORD)
        self.assertRechazada(resp)
        registro = TokenRecuperacion.objects.get(id_usuario=self.usuario, usado=False)
        self.assertIsNotNone(registro)
        # El mismo enlace sirve para reintentar con otra contraseña.
        resp = self.client.post(RESTABLECER_URL, {'token': token, 'password': NUEVAS[0]}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(self._password_actual_es(NUEVAS[0]))

    def test_edicion_por_admin_rechaza_la_actual(self):
        self.assertRechazada(self._editar_como_admin(PASSWORD))
        self.assertTrue(self._password_actual_es(PASSWORD))

    def test_rechaza_una_de_las_ultimas_cinco(self):
        self._cambiar_varias(NUEVAS[:5])  # historial: NUEVAS[3..0] y PASSWORD
        for anterior in (PASSWORD, NUEVAS[0], NUEVAS[3]):
            with self.subTest(anterior=anterior):
                self.assertRechazada(self._editar_como_admin(anterior))
                resp, _ = self._restablecer(anterior)
                self.assertRechazada(resp)
        self.assertTrue(self._password_actual_es(NUEVAS[4]))

    def test_rechazo_no_agrega_al_historial(self):
        self._cambiar_varias(NUEVAS[:2])
        antes = HistorialPassword.objects.filter(id_usuario=self.usuario).count()
        self.assertRechazada(self._editar_como_admin(NUEVAS[0]))
        self.assertEqual(HistorialPassword.objects.filter(id_usuario=self.usuario).count(), antes)

    # --- Aceptación ---

    def test_acepta_la_sexta_mas_antigua(self):
        # PASSWORD -> NUEVAS[0..5]: el historial queda con NUEVAS[4..0] y PASSWORD sale.
        self._cambiar_varias(NUEVAS[:6])
        resp, _ = self._restablecer(PASSWORD)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(self._password_actual_es(PASSWORD))

    def test_acepta_la_sexta_mas_antigua_por_edicion(self):
        self._cambiar_varias(NUEVAS[:6])
        self.assertEqual(self._editar_como_admin(PASSWORD).status_code, 200)

    # --- Historial ---

    def test_historial_no_guarda_texto_plano(self):
        usadas = [PASSWORD, *NUEVAS[:3]]
        self._cambiar_varias(NUEVAS[:3])
        hashes = list(HistorialPassword.objects.filter(id_usuario=self.usuario)
                      .values_list('password_hash', flat=True))
        self.assertEqual(len(hashes), 3)
        for hash_guardado in hashes:
            self.assertNotIn(hash_guardado, usadas)
            self.assertTrue(all(p not in hash_guardado for p in usadas))
            identify_hasher(hash_guardado)  # es un hash reconocible, no texto
        # Cada anterior es verificable contra su hash.
        for anterior in usadas[:3]:
            self.assertTrue(any(check_password(anterior, h) for h in hashes), anterior)

    def test_mantiene_como_maximo_cinco_registros(self):
        self._cambiar_varias(NUEVAS)  # 7 cambios
        historial = HistorialPassword.objects.filter(id_usuario=self.usuario)
        self.assertEqual(historial.count(), MAX_HISTORIAL_PASSWORD)
        # Se conservan las 5 anteriores más recientes: NUEVAS[5..1].
        hashes = list(historial.values_list('password_hash', flat=True))
        for anterior in NUEVAS[1:6]:
            self.assertTrue(any(check_password(anterior, h) for h in hashes), anterior)
        for descartada in (PASSWORD, NUEVAS[0]):
            self.assertFalse(any(check_password(descartada, h) for h in hashes), descartada)

    def test_crear_usuario_no_registra_historial(self):
        nuevo = crear_usuario('nuevo@test.cl', '33333333-3')
        self.assertFalse(HistorialPassword.objects.filter(id_usuario=nuevo).exists())

    def test_set_password_directo_tambien_registra(self):
        usuario = Usuario.objects.get(pk=self.usuario.pk)
        usuario.set_password(NUEVAS[0])
        usuario.save()
        self.assertEqual(HistorialPassword.objects.filter(id_usuario=usuario).count(), 1)

    # --- Validador global (manage.py changepassword y formularios de Django) ---

    def test_validador_de_django_rechaza_reutilizacion(self):
        with self.assertRaisesMessage(ValidationError, MENSAJE_PASSWORD_REUTILIZADA):
            validate_password(PASSWORD, self.usuario)
        validate_password(NUEVAS[0], self.usuario)  # una nueva pasa


class AdminUsuarioPasswordTests(TestCase):
    """En el admin la contraseña no se edita como texto; solo con el formulario de cambio."""

    def setUp(self):
        self.superusuario = Usuario.objects.create_superuser(
            'super@test.cl', '11111111-1', 'Ada', 'Admin', PASSWORD)
        self.usuario = crear_usuario('trabajador@test.cl', '22222222-2')
        self.client.force_login(self.superusuario)
        self.url_cambio = f'/admin/usuarios/usuario/{self.usuario.pk}/change/'
        self.url_password = f'/admin/usuarios/usuario/{self.usuario.pk}/password/'

    def test_password_es_de_solo_lectura_en_el_formulario(self):
        resp = self.client.get(self.url_cambio)
        self.assertEqual(resp.status_code, 200)
        campo = resp.context['adminform'].form.fields['password']
        self.assertIsInstance(campo, ReadOnlyPasswordHashField)
        self.assertTrue(campo.disabled)

    def test_post_con_password_en_texto_no_la_cambia(self):
        hash_antes = self.usuario.password
        resp = self.client.post(self.url_cambio, {
            'correo': self.usuario.correo, 'rut': self.usuario.rut,
            'nombres': self.usuario.nombres, 'apellidos': self.usuario.apellidos,
            'telefono': '', 'id_rol': Roles.TRABAJADOR, 'estado': 'activo', 'is_active': 'on',
            'password': 'texto-plano-123',
        })
        self.assertEqual(resp.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.password, hash_antes)
        self.assertFalse(HistorialPassword.objects.filter(id_usuario=self.usuario).exists())

    def test_formulario_de_cambio_aplica_el_historial(self):
        datos = {'usable_password': 'true'}
        resp = self.client.post(self.url_password, {**datos, 'password1': PASSWORD, 'password2': PASSWORD})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, MENSAJE_PASSWORD_REUTILIZADA)
        self.usuario.refresh_from_db()
        self.assertTrue(check_password(PASSWORD, self.usuario.password))

        resp = self.client.post(self.url_password, {**datos, 'password1': NUEVAS[0], 'password2': NUEVAS[0]})
        self.assertEqual(resp.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertTrue(check_password(NUEVAS[0], self.usuario.password))
        self.assertEqual(HistorialPassword.objects.filter(id_usuario=self.usuario).count(), 1)
