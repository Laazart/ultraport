import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0010_contrato_tipo_unico'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialPassword',
            fields=[
                ('id_historial', models.AutoField(primary_key=True, serialize=False)),
                ('password_hash', models.CharField(max_length=128)),
                ('fecha', models.DateTimeField(default=django.utils.timezone.now)),
                ('id_usuario', models.ForeignKey(
                    db_column='id_usuario',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historial_passwords',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'historial_password',
                'ordering': ['-fecha', '-id_historial'],
            },
        ),
    ]
