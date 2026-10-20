PLANTILLA_1_TURNO = [
    ('Naves y Embarcaciones', 'Movilizador Nave', 16, None),
    ('Naves y Embarcaciones', 'Capataz', 7, None),
    ('Naves y Embarcaciones', 'Hatchclerk', 5, None),
    ('Naves y Embarcaciones', 'Movilizador Nave Mineral', 4, None),
    ('Naves y Embarcaciones', 'Operador de Grúa Horquilla Tierra', 2, 'Grúa horquilla'),
    ('Naves y Embarcaciones', 'Capataz Mineral', 1, None),
    ('Naves y Embarcaciones', 'Tarjador', 1, None),
    ('Naves y Embarcaciones', 'Portalonero', 1, None),

    ('Patio de Contenedores', 'Operador de Tractocamión', 16, None),
    ('Patio de Contenedores', 'Operador de Portacontenedor', 4, None),
    ('Patio de Contenedores', 'Yard Cargo', 2, None),
    ('Patio de Contenedores', 'Oficinista Dispatcher', 1, None),

    ('Almacenes 1 y 4', 'Movilizador Tierra', 12, None),
    ('Almacenes 1 y 4', 'Movilizador Terrestre Maniobra', 4, None),
    ('Almacenes 1 y 4', 'Capataz Tierra Maniobra', 2, None),
    ('Almacenes 1 y 4', 'Tarjador', 2, None),
    ('Almacenes 1 y 4', 'Operador de Minicargador', 1, 'Minicargador'),
    ('Almacenes 1 y 4', 'Operador de Payloader', 1, 'Payloader'),
    ('Almacenes 1 y 4', 'Horquillero Tierra Picoloro', 1, None),
    ('Almacenes 1 y 4', 'Operador de Grúa Horquilla Tierra', 1, 'Grúa horquilla'),
]

TOTAL_CUPOS = sum(c for _, _, c, _ in PLANTILLA_1_TURNO)  