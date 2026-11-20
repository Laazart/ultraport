from django.db import migrations, models


class Migration(migrations.Migration):
    """Un contrato por tipo. Depende de la 0009, que antes fusiona los duplicados."""

    dependencies = [
        ('usuarios', '0009_fusionar_contratos_duplicados'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='contrato',
            constraint=models.UniqueConstraint(fields=('tipo',), name='uniq_contrato_tipo'),
        ),
    ]
