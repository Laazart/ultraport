from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin 
from .validar_rut import validar_rut_modulo_11, normalizar_rut
from django.core.validators import RegexValidator
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils import timezone

class Rol(models.Model):

    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=50, unique=True) 
    descripcion = models.CharField(max_length=255, null=True, blank=True) 

    def __str__(self):
        return self.nombre_rol
# --- CREACIÓN AUTOMÁTICA DE ROLES AL MIGRAR ---
@receiver(post_migrate)
def poblar_roles_iniciales(sender, **kwargs):
    if sender.name == 'usuarios':
        Rol = sender.get_model('Rol')
        roles_iniciales = [
            {
                "nombre_rol": "Administrador",
                "descripcion": "Responsable de gestion de inasistencia, ver malla de turnos, gestion de usuarios y contratos."
            },
            {
                "nombre_rol": "Encargado de Planificacion",
                "descripcion": "Responsable de gestion de inasistencia, imprimir reportes, malla de turnos, gestion de usuarios y contratos"
            },
            {
                "nombre_rol": "Trabajador",
                "descripcion": "Usuario con acceso a la malla de turnos, formulario de inasistencias, imprimir horario"
            },
        ]
        for rol in roles_iniciales:
            Rol.objects.get_or_create(
                nombre_rol=rol["nombre_rol"], defaults={"descripcion": rol["descripcion"]})
            
class Contrato(models.Model):

    id_contrato = models.AutoField(primary_key=True) 
    tipo = models.CharField(max_length=30)
    modalidad = models.CharField(max_length=20, null=True, blank=True)
    turno_habitual = models.CharField(max_length=20) 
    horas_semanales_pactadas = models.IntegerField() 
    permite_horas_extra = models.BooleanField(default=False) 
    max_noches_consecutivas = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True) 
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.tipo

class UsuarioManager(BaseUserManager):
    def create_user(self, correo, rut, nombres, apellidos, password=None, **extra_fields):
        if not correo:
            raise ValueError('El correo es obligatorio')
        user = self.model(
            correo=self.normalize_email(correo),
            rut=rut,
            nombres=nombres,
            apellidos=apellidos,
            **extra_fields
        )
        user.set_password(password) 
        user.save(using=self._db)
        return user

    def create_superuser(self, correo, rut, nombres, apellidos, password=None, **extra_fields):
        extra_fields.setdefault('estado', 'activo')
        extra_fields.setdefault('is_staff', True)    
        extra_fields.setdefault('is_superuser', True)  

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(correo, rut, nombres, apellidos, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):  
    id_usuario = models.AutoField(primary_key=True) 
    rut = models.CharField(max_length=12, unique=True, validators=[validar_rut_modulo_11],verbose_name="Rut")
    nombres = models.CharField(max_length=100) 
    apellidos = models.CharField(max_length=100) 
    correo = models.EmailField(max_length=150, unique=True) 
    regex_celular_chile = RegexValidator(regex=r'^9\d{8}$', message="El número de celular debe tener 9 dígitos y comenzar con 9 (ej: 947492086).")
    telefono = models.CharField( max_length=9, unique=True, null=True, blank=True,validators= [regex_celular_chile])
    id_rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, db_column='id_rol')  
    id_contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True,db_column='id_contrato') 
    estado = models.CharField(max_length=20, default='activo') 
    fecha_creacion = models.DateTimeField(default=timezone.now,editable=False)

    is_staff = models.BooleanField(default=False)  
    is_active = models.BooleanField(default=True)    

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo' 
    REQUIRED_FIELDS = ['rut', 'nombres', 'apellidos']

    def __str__(self):
        return f'{self.nombres} {self.apellidos}'

class TokenRecuperacion(models.Model):
    id_token = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column='id_usuario'
    )
    token_hash = models.CharField(max_length=255, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    usado = models.BooleanField(default=False)

    class Meta:
        db_table = 'token_recuperacion'