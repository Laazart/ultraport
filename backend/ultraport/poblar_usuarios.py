from django.db import transaction
from django.contrib.auth.hashers import make_password
from usuarios.models import (
    Rol, Contrato, Puesto, TipoLicencia, Maquinaria,
    Usuario, UsuarioPuesto, UsuarioLicencia, UsuarioMaquinaria,
)

def digito_verificador(num):
    suma, mult = 0, 2
    for d in reversed(str(num)):
        suma += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    resto = 11 - (suma % 11)
    return '0' if resto == 11 else 'K' if resto == 10 else str(resto)

TRABAJADORES = [
    (10000001, 'Juan', 'Perez', 'juan.perez@ultraport.cl', 'Movilizador Nave', 1),
    (10000002, 'Luis', 'Gonzalez', 'luis.gonzalez@ultraport.cl', 'Capataz', 2),
    (10000003, 'Carlos', 'Rojas', 'carlos.rojas@ultraport.cl', 'Hatchclerk', 3),
    (10000004, 'Miguel', 'Diaz', 'miguel.diaz@ultraport.cl', 'Movilizador Nave Mineral', 1),
    (10000005, 'Jose', 'Silva', 'jose.silva@ultraport.cl', 'Operador de Grúa Horquilla Tierra', 2),
    (10000006, 'Antonio', 'Soto', 'antonio.soto@ultraport.cl', 'Capataz Mineral', 3),
    (10000007, 'Francisco', 'Contreras', 'francisco.contreras@ultraport.cl', 'Tarjador', 1),
    (10000008, 'Diego', 'Lopez', 'diego.lopez@ultraport.cl', 'Portalonero', 2),
    (10000009, 'Jorge', 'Morales', 'jorge.morales@ultraport.cl', 'Operador de Tractocamión', 3),
    (10000010, 'Manuel', 'Sepulveda', 'manuel.sepulveda@ultraport.cl', 'Operador de Portacontenedor', 1),
    (10000011, 'Roberto', 'Fuentes', 'roberto.fuentes@ultraport.cl', 'Yard Cargo', 2),
    (10000012, 'Pedro', 'Rodriguez', 'pedro.rodriguez@ultraport.cl', 'Oficinista Dispatcher', 3),
    (10000013, 'Eduardo', 'Valdes', 'eduardo.valdes@ultraport.cl', 'Movilizador Tierra', 1),
    (10000014, 'Mario', 'Castillo', 'mario.castillo@ultraport.cl', 'Movilizador Terrestre Maniobra', 2),
    (10000015, 'Cristian', 'Pizarro', 'cristian.pizarro@ultraport.cl', 'Capataz Tierra Maniobra', 3),
    (10000016, 'Ricardo', 'Gomez', 'ricardo.gomez@ultraport.cl', 'Operador de Minicargador', 1),
    (10000017, 'Marcelo', 'Cortes', 'marcelo.cortes@ultraport.cl', 'Operador de Payloader', 2),
    (10000018, 'Felipe', 'Herrera', 'felipe.herrera@ultraport.cl', 'Horquillero Tierra Picoloro', 3),
    (10000019, 'Rodrigo', 'Fernandez', 'rodrigo.fernandez@ultraport.cl', 'Movilizador Nave', 1),
    (10000020, 'Fernando', 'Muñoz', 'fernando.munoz@ultraport.cl', 'Capataz', 2),
    (10000021, 'Patricio', 'Tapia', 'patricio.tapia@ultraport.cl', 'Hatchclerk', 3),
    (10000022, 'Victor', 'Espinoza', 'victor.espinoza@ultraport.cl', 'Movilizador Nave Mineral', 1),
    (10000023, 'Hugo', 'Ramirez', 'hugo.ramirez@ultraport.cl', 'Operador de Grúa Horquilla Tierra', 2),
    (10000024, 'Gabriel', 'Alvarez', 'gabriel.alvarez@ultraport.cl', 'Capataz Mineral', 3),
    (10000025, 'Alejandro', 'Vargas', 'alejandro.vargas@ultraport.cl', 'Tarjador', 1),
    (10000026, 'Julio', 'Castro', 'julio.castro@ultraport.cl', 'Portalonero', 2),
    (10000027, 'Guillermo', 'Vergara', 'guillermo.vergara@ultraport.cl', 'Operador de Tractocamión', 3),
    (10000028, 'Andres', 'Guzman', 'andres.guzman@ultraport.cl', 'Operador de Portacontenedor', 1),
    (10000029, 'Sergio', 'Rios', 'sergio.rios@ultraport.cl', 'Yard Cargo', 2),
    (10000030, 'Oscar', 'Salinas', 'oscar.salinas@ultraport.cl', 'Oficinista Dispatcher', 3),
    (10000031, 'Hector', 'Navarro', 'hector.navarro@ultraport.cl', 'Movilizador Tierra', 1),
    (10000032, 'Claudio', 'Araya', 'claudio.araya@ultraport.cl', 'Movilizador Terrestre Maniobra', 2),
    (10000033, 'Enrique', 'Zuñiga', 'enrique.zuniga@ultraport.cl', 'Capataz Tierra Maniobra', 3),
    (10000034, 'Mauricio', 'Orellana', 'mauricio.orellana@ultraport.cl', 'Operador de Minicargador', 1),
    (10000035, 'Gonzalo', 'Caceres', 'gonzalo.caceres@ultraport.cl', 'Operador de Payloader', 2),
    (10000036, 'Javier', 'Garrido', 'javier.garrido@ultraport.cl', 'Horquillero Tierra Picoloro', 3),
    (10000037, 'Pablo', 'Bravo', 'pablo.bravo@ultraport.cl', 'Movilizador Nave', 1),
    (10000038, 'Daniel', 'Vera', 'daniel.vera@ultraport.cl', 'Capataz', 2),
    (10000039, 'Tomas', 'Poblete', 'tomas.poblete@ultraport.cl', 'Hatchclerk', 3),
    (10000040, 'Martin', 'Pino', 'martin.pino@ultraport.cl', 'Movilizador Nave Mineral', 1),
    (10000041, 'Raul', 'Molina', 'raul.molina@ultraport.cl', 'Operador de Grúa Horquilla Tierra', 2),
    (10000042, 'Arturo', 'Moya', 'arturo.moya@ultraport.cl', 'Capataz Mineral', 3),
    (10000043, 'Ivan', 'Olivares', 'ivan.olivares@ultraport.cl', 'Tarjador', 1),
    (10000044, 'Alfonso', 'Aguilar', 'alfonso.aguilar@ultraport.cl', 'Portalonero', 2),
    (10000045, 'Matias', 'Gallo', 'matias.gallo@ultraport.cl', 'Operador de Tractocamión', 3),
    (10000046, 'Eugenio', 'Salgado', 'eugenio.salgado@ultraport.cl', 'Operador de Portacontenedor', 1),
    (10000047, 'Nelson', 'Bustamante', 'nelson.bustamante@ultraport.cl', 'Yard Cargo', 2),
    (10000048, 'Ruben', 'Figueroa', 'ruben.figueroa@ultraport.cl', 'Oficinista Dispatcher', 3),
    (10000049, 'Esteban', 'Reyes', 'esteban.reyes@ultraport.cl', 'Movilizador Tierra', 1),
    (10000050, 'Ignacio', 'Lara', 'ignacio.lara@ultraport.cl', 'Movilizador Terrestre Maniobra', 2),
    (10000051, 'Rene', 'Vega', 'rene.vega@ultraport.cl', 'Capataz Tierra Maniobra', 3),
    (10000052, 'Gustavo', 'Carvajal', 'gustavo.carvajal@ultraport.cl', 'Operador de Minicargador', 1),
    (10000053, 'Cesar', 'Arias', 'cesar.arias@ultraport.cl', 'Operador de Payloader', 2),
    (10000054, 'Domingo', 'Campos', 'domingo.campos@ultraport.cl', 'Horquillero Tierra Picoloro', 3),
    (10000055, 'Felix', 'Cornejo', 'felix.cornejo@ultraport.cl', 'Movilizador Nave', 1),
    (10000056, 'Hernan', 'Alonso', 'hernan.alonso@ultraport.cl', 'Capataz', 2),
    (10000057, 'Ramon', 'Valenzuela', 'ramon.valenzuela@ultraport.cl', 'Hatchclerk', 3),
    (10000058, 'Ismael', 'Peña', 'ismael.pena@ultraport.cl', 'Movilizador Nave Mineral', 1),
    (10000059, 'Bastian', 'Donoso', 'bastian.donoso@ultraport.cl', 'Operador de Grúa Horquilla Tierra', 2),
    (10000060, 'Elias', 'Vidal', 'elias.vidal@ultraport.cl', 'Capataz Mineral', 3),
    (10000061, 'Joaquin', 'Ramos', 'joaquin.ramos@ultraport.cl', 'Tarjador', 1),
    (10000062, 'Lorenzo', 'Cruz', 'lorenzo.cruz@ultraport.cl', 'Portalonero', 2),
    (10000063, 'Sebastian', 'Leal', 'sebastian.leal@ultraport.cl', 'Operador de Tractocamión', 3),
    (10000064, 'Simon', 'Paredes', 'simon.paredes@ultraport.cl', 'Operador de Portacontenedor', 1),
    (10000065, 'Agustin', 'Paz', 'agustin.paz@ultraport.cl', 'Yard Cargo', 2),
    (10000066, 'Benjamin', 'Osorio', 'benjamin.osorio@ultraport.cl', 'Oficinista Dispatcher', 3),
    (10000067, 'Samuel', 'Carrasco', 'samuel.carrasco@ultraport.cl', 'Movilizador Tierra', 1),
    (10000068, 'Lucas', 'Rivera', 'lucas.rivera@ultraport.cl', 'Movilizador Terrestre Maniobra', 2),
    (10000069, 'Vicente', 'Mendez', 'vicente.mendez@ultraport.cl', 'Capataz Tierra Maniobra', 3),
    (10000070, 'Gaston', 'Parra', 'gaston.parra@ultraport.cl', 'Operador de Minicargador', 1),
    (10000071, 'Emilio', 'Miranda', 'emilio.miranda@ultraport.cl', 'Operador de Payloader', 2),
    (10000072, 'Ernesto', 'Medina', 'ernesto.medina@ultraport.cl', 'Horquillero Tierra Picoloro', 3),
    (10000073, 'Bernardo', 'Salazar', 'bernardo.salazar@ultraport.cl', 'Movilizador Nave', 1),
    (10000074, 'Camilo', 'Arriagada', 'camilo.arriagada@ultraport.cl', 'Capataz', 2),
    (10000075, 'Ariel', 'Escobar', 'ariel.escobar@ultraport.cl', 'Hatchclerk', 3),
    (10000076, 'Rolando', 'Villalobos', 'rolando.villalobos@ultraport.cl', 'Movilizador Nave Mineral', 1),
    (10000077, 'Gerardo', 'Godoy', 'gerardo.godoy@ultraport.cl', 'Operador de Grúa Horquilla Tierra', 2),
    (10000078, 'Omar', 'Caceres', 'omar.caceres@ultraport.cl', 'Capataz Mineral', 3),
    (10000079, 'Fidel', 'Nuñez', 'fidel.nunez@ultraport.cl', 'Tarjador', 1),
    (10000080, 'Armando', 'Ponce', 'armando.ponce@ultraport.cl', 'Portalonero', 2),
    (10000081, 'Jaime', 'Galvez', 'jaime.galvez@ultraport.cl', 'Operador de Tractocamión', 3),
    (10000082, 'Maximiliano', 'San Martin', 'maximiliano.sanmartin@ultraport.cl', 'Operador de Portacontenedor', 1),
    (10000083, 'Julian', 'Becerra', 'julian.becerra@ultraport.cl', 'Yard Cargo', 2),
    (10000084, 'Mateo', 'Cerda', 'mateo.cerda@ultraport.cl', 'Oficinista Dispatcher', 3),
    (10000085, 'Leonel', 'Jara', 'leonel.jara@ultraport.cl', 'Movilizador Tierra', 1),
    (10000086, 'Oliver', 'Guerrero', 'oliver.guerrero@ultraport.cl', 'Movilizador Terrestre Maniobra', 2),
    (10000087, 'Nicolas', 'Farias', 'nicolas.farias@ultraport.cl', 'Capataz Tierra Maniobra', 3),
    (10000088, 'Ian', 'Catalan', 'ian.catalan@ultraport.cl', 'Operador de Minicargador', 1),
    (10000089, 'Alonso', 'Ortiz', 'alonso.ortiz@ultraport.cl', 'Operador de Payloader', 2),
    (10000090, 'Kevin', 'Pacheco', 'kevin.pacheco@ultraport.cl', 'Horquillero Tierra Picoloro', 3),
    (10000091, 'Cristobal', 'Avila', 'cristobal.avila@ultraport.cl', 'Movilizador Nave', 1),
    (10000092, 'Maximo', 'Ulloa', 'maximo.ulloa@ultraport.cl', 'Capataz', 2),
    (10000093, 'Alex', 'Saavedra', 'alex.saavedra@ultraport.cl', 'Hatchclerk', 3),
    (10000094, 'Marcos', 'Lagos', 'marcos.lagos@ultraport.cl', 'Movilizador Nave Mineral', 1),
    (10000095, 'Renato', 'Oyarzun', 'renato.oyarzun@ultraport.cl', 'Operador de Grúa Horquilla Tierra', 2),
    (10000096, 'Leonardo', 'Aguilera', 'leonardo.aguilera@ultraport.cl', 'Capataz Mineral', 3),
    (10000097, 'Emanuel', 'Cabrera', 'emanuel.cabrera@ultraport.cl', 'Tarjador', 1),
    (10000098, 'Moises', 'Retamal', 'moises.retamal@ultraport.cl', 'Portalonero', 2),
    (10000099, 'Boris', 'Inostroza', 'boris.inostroza@ultraport.cl', 'Operador de Tractocamión', 3),
    (10000100, 'David', 'Palacios', 'david.palacios@ultraport.cl', 'Operador de Portacontenedor', 1),
]

LICENCIA_POR_PUESTO = {
    'Operador de Tractocamión': 'A3',
    'Operador de Portacontenedor': 'A3',
    'Operador de Grúa Horquilla Tierra': 'D',
    'Operador de Minicargador': 'D',
    'Operador de Payloader': 'D',
    'Horquillero Tierra Picoloro': 'D',
}

rol = Rol.objects.get(id_rol=3)
password = make_password('clave12345')
contratos = {c.id_contrato: c for c in Contrato.objects.all()}
puestos = {p.nombre_puesto: p for p in Puesto.objects.all()}
licencias = {t.nombre_licencia: t for t in TipoLicencia.objects.all()}

with transaction.atomic():
    for numero, nombres, apellidos, correo, puesto_nombre, contrato_id in TRABAJADORES:
        if Usuario.objects.filter(correo=correo).exists():
            print('Ya existe, se omite:', correo)
            continue
        usuario = Usuario.objects.create(
            rut=f'{numero}-{digito_verificador(numero)}',
            nombres=nombres,
            apellidos=apellidos,
            correo=correo,
            telefono=None,
            id_rol=rol,
            id_contrato=contratos[contrato_id],
            estado='activo',
            is_active=True,
            password=password,
        )
        puesto = puestos[puesto_nombre]
        UsuarioPuesto.objects.create(id_usuario=usuario, id_puesto=puesto)
        UsuarioLicencia.objects.create(
            id_usuario=usuario,
            id_tipo_licencia=licencias[LICENCIA_POR_PUESTO.get(puesto_nombre, 'B')],
            especialidades=puesto.nombre_puesto,
            fecha_emision='2025-01-01',
            fecha_vencimiento='2028-01-01',
        )
        maquina = Maquinaria.objects.filter(id_puesto_asociado=puesto).first()
        if maquina:
            UsuarioMaquinaria.objects.create(id_usuario=usuario, id_maquinaria=maquina, fecha_vencimiento='2028-01-01')

print('Usuarios de trabajo totales en la BD:', Usuario.objects.filter(id_rol=rol).count())