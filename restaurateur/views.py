import requests

from itertools import chain
from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View


from geopy import distance
from environs import Env

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem
from place.models import Place


env = Env()
env.read_env()


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission

def get_or_create_place(list_address, obj_place):
    yandex_geocoder_api_key = env.str('YANDEX_GEOCODER_API_KEY')
    place_address = [address.address for address in obj_place]
    for address in list_address:
        if not address in place_address:
            coordinates = fetch_coordinates(yandex_geocoder_api_key, address)
            if coordinates:
                Place.objects.create(
                    address=address,
                    lat=coordinates[1],
                    lon=coordinates[0],
                )


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )
    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    # находим все заказы исключая статус 4, 'Завершен'
    orders_with_total_cost = []
    orders = Order.objects.all().prefetch_related('products').exclude(status=4).with_total_cost().order_by('status')

    # находим какие продукты делают  рестораны
    restaurant_menu_items_payload = {}
    restaurant_menu_items = RestaurantMenuItem.objects.filter(availability=True)\
        .values_list('restaurant__name', 'product')
    [restaurant_menu_items_payload.setdefault(key, []).append(value) for key, value in list(restaurant_menu_items)]

    # находим продукты в каждом заказе
    order_products = {order.id: [product.id for product in order.products.all()] for order in orders}

    # находим какие рестораны смогут выполнить заказ
    available_restaurants = {ord_key: [rest_key for rest_key, rest_list in restaurant_menu_items_payload.items()
              if set(ord_list).issubset(set(rest_list))] for
              ord_key, ord_list in order_products.items()}

    # находим все рестораны и их адреса
    all_restaurant = {}
    [all_restaurant.setdefault(key, value) for key, value in Restaurant.objects.all().values_list('name', 'address')]
    restaurant_address = list(all_restaurant.values())

    # находим все адреса заказов
    address = [address for address in orders.values_list('address')]
    order_address = list(chain.from_iterable(address))

    # объединяем адреса, проверяем и записываем координаты адресов в модель Place
    all_address = restaurant_address + order_address
    obj_places = Place.objects.all()
    get_or_create_place(all_address, obj_places)

    # добавляем в список рестораны ктр. могут приготовить продукты
    for index, key in enumerate(available_restaurants):
        order_payload = {
            'order': orders[index],
            'restaurants': available_restaurants[key]
        }
        orders_with_total_cost.append(order_payload)

    # находим все места по адресам указанным в текущих заказах
    places = Place.objects.filter(address__in=all_address)
    # создаем словарь для быстрого доступа к объектам Place по адресу
    place_dict = {place.address: place for place in places}

    # вычисляем дистанцию от каждого ресторана ктр. может доставить продукцию до адреса доставки
    all_distance = []
    for order in orders_with_total_cost:
        client_address = order['order'].address
        client_place = place_dict.get(client_address)
        if client_place:
            delivery_distance = []
            for restaurant in order['restaurants']:
                restaurant_address = all_restaurant.get(restaurant)
                restaurant_place = place_dict.get(restaurant_address)
                client_coordinates = [client_place.lat, client_place.lon]
                restaurant_coordinates = [client_place.lat, restaurant_place.lon]
                distance_km = round(distance.distance(client_coordinates, restaurant_coordinates).km, 2)
                delivery_distance.append((f'{restaurant} - {distance_km} км.'))
            all_distance.append(delivery_distance)
        else:
            all_distance.append(['Неправильно указан адрес'])

    # добавляем в список дистанцию доставки
    for index, order in enumerate(orders_with_total_cost):
        orders_with_total_cost[index]['distance'] = all_distance[index]

    return render(request, template_name='order_items.html', context={
        'order_items': orders_with_total_cost,
    })

