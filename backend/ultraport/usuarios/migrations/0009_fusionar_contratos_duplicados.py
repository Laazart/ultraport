"""
Fusiona contratos duplicados.

Contrato es un tipo compartido (bono_turno, cppt, eventual): varios usuarios
apuntan a la misma fila. Un script de datos de prueba creó una copia idéntica
por trabajador. Aquí, por cada grupo de contratos con los mismos valores, se
conserva el de menor id, se mueven sus usuarios a él y se borran las copias.

Si después de fusionar quedan dos contratos del mismo tipo con valores
distintos, la migración se detiene: la restricción única de la 0010 fallaría y
hay que decidir a mano cuál conservar.

Reversa: no hace nada. No se puede saber a qué copia apuntaba cada usuario y,
como las copias eran idénticas, revertir no cambiaría ninguna regla.
"""
from collections import defaultdict

from django.db import migrations

# Todo lo que define el contrato; se excluyen la PK y las marcas de tiempo.
CAMPOS_COMPARADOS = [
    'tipo', 'modalidad', 'turno_habitual', 'horas_semanales_pactadas',
    'permite_horas_extra', 'max_noches_consecutivas', 'max_noches_semana',
    'fecha_inicio', 'fecha_termino',
]


def fusionar_duplicados(apps, schema_editor):
    Contrato = apps.get_model('usuarios', 'Contrato')
    Usuario = apps.get_model('usuarios', 'Usuario')

    grupos = defaultdict(list)
    for fila in Contrato.objects.order_by('id_contrato').values('id_contrato', *CAMPOS_COMPARADOS):
        grupos[tuple(fila[c] for c in CAMPOS_COMPARADOS)].append(fila['id_contrato'])

    for ids in grupos.values():
        conservado, *duplicados = ids
        if duplicados:
            Usuario.objects.filter(id_contrato_id__in=duplicados).update(id_contrato_id=conservado)
            Contrato.objects.filter(id_contrato__in=duplicados).delete()

    por_tipo = defaultdict(list)
    for id_contrato, tipo in Contrato.objects.order_by('id_contrato').values_list('id_contrato', 'tipo'):
        por_tipo[tipo].append(id_contrato)
    conflictos = {tipo: ids for tipo, ids in por_tipo.items() if len(ids) > 1}
    if conflictos:
        detalle = '; '.join(f'{tipo}: ids {ids}' for tipo, ids in sorted(conflictos.items()))
        raise RuntimeError(
            'Hay contratos del mismo tipo con valores distintos y no se pueden fusionar '
            f'automáticamente ({detalle}). Reasigna sus usuarios y borra los sobrantes antes de migrar.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_auto_20261027_1638'),
    ]

    operations = [
        migrations.RunPython(fusionar_duplicados, migrations.RunPython.noop),
    ]
