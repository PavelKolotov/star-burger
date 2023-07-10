from django.db import models
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import F, Sum
from django.utils import timezone


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name



class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=300,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):

    def with_total_cost(self):
        return self.annotate(total_cost=Sum(F('order_items__price') * F('order_items__quantity')))


class Order(models.Model):

    STATUS_CHOICES = [
        (0, 'Необработанный'),
        (1, 'Принят'),
        (2, 'Передан в ресторан'),
        (3, 'Передан курьеру'),
        (4, 'Завершен')
    ]

    PAYMENTSTATUS_CHOICES = [
        (0, 'Наличный расчет'),
        (1, 'Безналичный расчет'),
        (2, 'Расчет переводом'),
    ]

    status = models.IntegerField(
        'Статус',
        choices=STATUS_CHOICES,
        default=0,
        db_index=True
    )

    paymentstatus = models.IntegerField(
        'Способ оплаты',
        choices=PAYMENTSTATUS_CHOICES,
        default=0,
        db_index=True
    )

    firstname = models.CharField(
        'Имя',
        max_length=20,
        db_index=True
    )
    lastname = models.CharField(
        'Фамилия',
        max_length=20,
        db_index=True
    )
    address = models.CharField(
        'Адрес',
        max_length=100
    )
    phonenumber = PhoneNumberField(
        'Контактный телефон'
    )
    comment = models.TextField(
        'Комментарий',
        max_length=200,
        blank=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='Ресторан',
        related_name='restaurants',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(
        'Время создания заказа',
        default=timezone.now,
        db_index=True
    )
    call_time = models.DateTimeField(
        'Время звонока',
        null=True,
        blank=True,
        db_index=True
    )
    completed_at = models.DateTimeField(
        'Время завершения заказа',
        null=True,
        blank=True,
        db_index=True
    )
    products = models.ManyToManyField(Product, through='OrderItem')

    objects = OrderQuerySet.as_manager()


    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'Order #{self.id}: {self.firstname} {self.lastname} - {self.address}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='order_items',
        verbose_name='заказ',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        related_name='product_items',
        verbose_name='товар',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(
        verbose_name='количество',
        default=1
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )


    class Meta:
        verbose_name = 'элементы заказа',
        verbose_name_plural = 'элементы заказа'

    def __str__(self):
        return f'{self.order} - {self.product.name} ({self.quantity})'
