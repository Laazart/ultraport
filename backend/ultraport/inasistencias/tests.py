from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from usuarios.models import Rol, Usuario
from usuarios.permissions import Roles
from .models import NotificacionInasistencia

URL = '/api/inasistencias/'
"""pruebas automatizadas"""
@override_settings(MEDIA_ROOT='test_media')
class NotificacionInasistenciaTests(APITestCase):
    def setUp(self):
        # los roles los crea la señal post_migrate de usuarios con los ids de Roles
        rol_trabajador = Rol.objects.get(pk=Roles.TRABAJADOR)
        rol_encargado = Rol.objects.get(pk=Roles.PLANIFICADOR)
        self.trabajador = Usuario.objects.create_user(
            'trabajador@test.cl', '11111111-1', 'Juan', 'Pérez', 'clave-segura-123',
            id_rol=rol_trabajador, telefono='912345678')
        self.otro = Usuario.objects.create_user(
            'otro@test.cl', '22222222-2', 'Ana', 'Soto', 'clave-segura-123', id_rol=rol_trabajador)
        self.encargado = Usuario.objects.create_user(
            'encargado@test.cl', '33333333-3', 'Luis', 'Rojas', 'clave-segura-123', id_rol=rol_encargado)

    def _crear(self, usuario, **extra):
        return NotificacionInasistencia.objects.create(
            id_usuario=usuario, motivo='Licencia', fecha_inicio='2026-10-20', **extra)

    def test_trabajador_crea_aviso_en_estado_pendiente(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.post(URL, {
            'motivo': 'Enfermedad', 'fecha_inicio': '2026-10-20', 'fecha_fin': '2026-10-22',
            'estado': 'aprobado',  # debe ignorarse
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['estado'], 'pendiente')
        self.assertEqual(resp.data['id_usuario'], self.trabajador.id_usuario)

    def test_crear_con_adjunto(self):
        self.client.force_authenticate(self.trabajador)
        archivo = SimpleUploadedFile('licencia.pdf', b'%PDF-1.4', content_type='application/pdf')
        resp = self.client.post(URL, {
            'motivo': 'Licencia médica', 'fecha_inicio': '2026-10-20', 'url_adjunto': archivo,
        }, format='multipart')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('/media/inasistencias/', resp.data['url_adjunto'])

    def test_rechaza_adjunto_no_permitido(self):
        self.client.force_authenticate(self.trabajador)
        archivo = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        resp = self.client.post(URL, {
            'motivo': 'x', 'fecha_inicio': '2026-10-20', 'url_adjunto': archivo,
        }, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_campos_obligatorios(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.post(URL, {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('motivo', resp.data)
        self.assertIn('fecha_inicio', resp.data)

    def test_fecha_fin_anterior_a_inicio(self):
        self.client.force_authenticate(self.trabajador)
        resp = self.client.post(URL, {
            'motivo': 'x', 'fecha_inicio': '2026-10-20', 'fecha_fin': '2026-10-19',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fecha_fin', resp.data)

    def test_requiere_autenticacion(self):
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_trabajador_solo_ve_sus_avisos(self):
        self._crear(self.trabajador)
        self._crear(self.otro)
        self.client.force_authenticate(self.trabajador)
        resp = self.client.get(URL)
        self.assertEqual(len(resp.data), 1)

    def test_encargado_ve_todos_y_filtra_por_estado(self):
        self._crear(self.trabajador)
        self._crear(self.otro, estado='aprobado')
        self.client.force_authenticate(self.encargado)
        self.assertEqual(len(self.client.get(URL).data), 2)
        aprobados = self.client.get(URL, {'estado': 'aprobado'}).data
        self.assertEqual(len(aprobados), 1)
        pendiente = self.client.get(URL, {'estado': 'pendiente'}).data[0]
        self.assertEqual(pendiente['usuario']['telefono'], '912345678')

    def test_encargado_no_registra_avisos(self):
        self.client.force_authenticate(self.encargado)
        resp = self.client.post(URL, {'motivo': 'x', 'fecha_inicio': '2026-10-20'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_encargado_cambia_estado_y_puede_revertirlo(self):
        aviso = self._crear(self.trabajador)
        self.client.force_authenticate(self.encargado)
        url = f'{URL}{aviso.id_notificacion}/estado/'
        for estado in ('aprobado', 'rechazado', 'pendiente'):
            resp = self.client.patch(url, {'estado': estado}, format='json')
            self.assertEqual(resp.status_code, 200)
            aviso.refresh_from_db()
            self.assertEqual(aviso.estado, estado)

    def test_estado_invalido(self):
        aviso = self._crear(self.trabajador)
        self.client.force_authenticate(self.encargado)
        resp = self.client.patch(f'{URL}{aviso.id_notificacion}/estado/', {'estado': 'otro'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_trabajador_no_puede_cambiar_estado(self):
        aviso = self._crear(self.trabajador)
        self.client.force_authenticate(self.trabajador)
        resp = self.client.patch(f'{URL}{aviso.id_notificacion}/estado/', {'estado': 'aprobado'}, format='json')
        self.assertEqual(resp.status_code, 403)
