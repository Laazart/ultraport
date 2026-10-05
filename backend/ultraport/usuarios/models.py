from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin 


class Rol(models.Model):

    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=50, unique=True) 
    descripcion = models.CharField(max_length=255, null=True, blank=True) 

    def __str__(self):
        return self.nombre_rol
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
    rut = models.CharField(max_length=12, unique=True)
    nombres = models.CharField(max_length=100) 
    apellidos = models.CharField(max_length=100) 
    correo = models.EmailField(max_length=150, unique=True) 
    id_rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True) 
    id_contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True) 
    estado = models.CharField(max_length=20, default='activo') 
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)  
    is_active = models.BooleanField(default=True)    

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo' 
    REQUIRED_FIELDS = ['rut', 'nombres', 'apellidos']

    def __str__(self):
        return f'{self.nombres} {self.apellidos}'