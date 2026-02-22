# Generated manually - documento_identidad nullable

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0003_alter_logacceso_tipo_evento_alter_usuario_rol"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usuario",
            name="documento_identidad",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=20,
                unique=True,
                verbose_name="Documento de identidad",
            ),
        ),
    ]
