# Generated by Django 4.2.3 on 2023-07-09 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0052_alter_order_paymentstatus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='paymentstatus',
            field=models.IntegerField(choices=[(0, 'Наличный расчет'), (1, 'Безналичный расчет'), (2, 'Расчет переводом')], db_index=True, default=0, max_length=20, verbose_name='Способ оплаты'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.IntegerField(choices=[(0, 'Необработанный'), (1, 'Принят'), (2, 'Передан в ресторан'), (3, 'Передан курьеру'), (4, 'Завершен')], db_index=True, default=0, max_length=20, verbose_name='Статус'),
        ),
    ]
