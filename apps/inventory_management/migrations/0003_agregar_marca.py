# Generated manually

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('inventory_management', '0002_producto_iva'),
    ]

    operations = [
        # 1. PRIMERO: Crear el modelo Marca
        migrations.CreateModel(
            name='Marca',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nombre', models.CharField(help_text='Nombre de la marca', max_length=100, unique=True)),
                ('descripcion', models.TextField(blank=True, help_text='Descripción de la marca y sus productos')),
                ('pais_origen', models.CharField(blank=True, help_text='País de origen de la marca', max_length=100)),
                ('fabricante', models.CharField(blank=True, help_text='Empresa fabricante o dueña de la marca', max_length=200)),
                ('logo', models.ImageField(blank=True, help_text='Logo de la marca', null=True, upload_to='marcas/')),
                ('sitio_web', models.URLField(blank=True, help_text='Sitio web oficial de la marca')),
                ('activa', models.BooleanField(default=True, help_text='Marca activa en el sistema')),
                ('destacada', models.BooleanField(default=False, help_text='Marca destacada (para mostrar en reportes o destacados)')),
                ('orden', models.IntegerField(default=0, help_text='Orden de visualización')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Marca',
                'verbose_name_plural': 'Marcas',
                'db_table': 'inv_marca',
                'ordering': ['orden', 'nombre'],
            },
        ),
        
        # 2. SEGUNDO: Agregar el campo marca a Producto
        migrations.AddField(
            model_name='producto',
            name='marca',
            field=models.ForeignKey(
                blank=True,
                help_text='Marca del producto',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='productos',
                to='inventory_management.marca'
            ),
        ),
        
        # 3. TERCERO: Crear índices (DESPUÉS de que el campo existe)
        migrations.AddIndex(
            model_name='marca',
            index=models.Index(fields=['nombre'], name='inv_marca_nombre_190388_idx'),
        ),
        migrations.AddIndex(
            model_name='marca',
            index=models.Index(fields=['activa', 'orden'], name='inv_marca_activa_3b3b67_idx'),
        ),
        migrations.AddIndex(
            model_name='marca',
            index=models.Index(fields=['destacada', 'activa'], name='inv_marca_destaca_7c9bf2_idx'),
        ),
        migrations.AddIndex(
            model_name='producto',
            index=models.Index(fields=['marca', 'activo'], name='inv_product_marca_i_836103_idx'),
        ),
    ]