# Generated by Django 3.2.15 on 2023-07-04 21:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0040_auto_20230704_2120'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='orderitem',
            options={'verbose_name': ('элементы заказа',), 'verbose_name_plural': 'элементы заказа'},
        ),
    ]
