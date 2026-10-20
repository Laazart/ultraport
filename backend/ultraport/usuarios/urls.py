from django.urls import path,include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomLoginView, LogoutView, RestablecerPasswordView, SolicitarRecuperacionView, UsuarioViewSet, RolViewSet,  ContratoViewSet, PuestoViewSet, TipoLicenciaViewSet, MaquinariaViewSet, UsuarioPuestoViewSet, UsuarioLicenciaViewSet, UsuarioMaquinariaViewSet 
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('usuarios', UsuarioViewSet, basename='usuario')
router.register('roles', RolViewSet, basename='roles')
router.register('contratos', ContratoViewSet, basename='contratos')
router.register('puestos', PuestoViewSet, basename='puestos')
router.register('tipos-licencia', TipoLicenciaViewSet, basename='tipos-licencia')
router.register('maquinarias', MaquinariaViewSet, basename='maquinarias')
router.register('usuario-puestos', UsuarioPuestoViewSet, basename='usuario-puestos')
router.register('usuario-licencias', UsuarioLicenciaViewSet, basename='usuario-licencias')
router.register('usuario-maquinarias', UsuarioMaquinariaViewSet, basename='usuario-maquinarias')

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('recuperar-password/', SolicitarRecuperacionView.as_view(), name='solicitar_recuperacion'),
    path('restablecer-password/', RestablecerPasswordView.as_view(), name='restablecer_password'),
    path('', include(router.urls)),
]