from django.db import models
from django.utils import timezone


class Place(models.Model):
    address = models.CharField('Адрес', max_length=100)
    lat = models.DecimalField('Широта', max_digits=9, decimal_places=6, blank=True, null=True)
    lon = models.DecimalField('Долгота', max_digits=9, decimal_places=6, blank=True, null=True)
    geocode_date = models.DateField('Дата запроса', default=timezone.now,)

    class Meta:
        unique_together = ['lat', 'lon', 'address']

    def __str__(self):
        return self.address
