# Generated by Django 4.2.3 on 2023-07-17 20:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0055_alter_order_paymentstatus'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='paymentstatus',
            new_name='payment_method',
        ),
    ]