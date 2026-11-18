from django.db import migrations

HORARIOS_OFICIALES = {
    1: ('08:00:00', '15:30:00'),
    2: ('15:30:00', '23:00:00'),
    3: ('23:00:00', '06:30:00'),
}

HORARIOS_ANTERIORES = {
    1: ('08:00:00', '13:00:00'),
    2: ('14:00:00', '22:00:00'),
    3: ('23:00:00', '07:00:00'),
}


def _aplicar(horarios):
    def operacion(apps, schema_editor):
        BloqueTurno = apps.get_model('horario', 'BloqueTurno')
        for orden, (inicio, termino) in horarios.items():
            BloqueTurno.objects.filter(orden_secuencia=orden).update(
                hora_inicio=inicio, hora_termino=termino,
            )
    return operacion


class Migration(migrations.Migration):

    dependencies = [
        ('horario', '0003_auto_20261027_1652'),
    ]

    operations = [
        migrations.RunPython(_aplicar(HORARIOS_OFICIALES), _aplicar(HORARIOS_ANTERIORES)),
    ]
