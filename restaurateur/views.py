import requests
from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from geopy import distance
from environs import Env

from foodcartapp.models import Product, Restaurant, Order
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
    orders_with_total_cost = []
    yandex_geocoder_api_key = env.str('YANDEX_GEOCODER_API_KEY')
    orders = Order.objects.exclude(status=4).prefetch_related('order_items__product').with_total_cost().order_by(
        'status')

    for order in orders:
        order_items = {}
        restaurants = []
        order_items['order'] = order

        products = order.products.all()

        available_restaurants = Restaurant.objects.filter(
            menu_items__product__in=products,
            menu_items__availability=True
        ).annotate(num_available_products=Count('menu_items__product')).filter(
            num_available_products=len(products)
        )

        for restaurant in available_restaurants:
            restaurant_address = restaurant.address
            restaurant_place = Place.objects.filter(address=restaurant_address)

            if not restaurant_place:
                restaurant_coordinates = fetch_coordinates(yandex_geocoder_api_key, restaurant_address)
                Place.objects.create(
                    address=restaurant_address,
                    lat=restaurant_coordinates[1],
                    lon=restaurant_coordinates[0],
                )
            else:
                restaurant_coordinates = [restaurant_place[0].lon, restaurant_place[0].lat]

            client_address = order.address
            client_place = Place.objects.filter(address=client_address)

            if not client_place:
                client_coordinates = fetch_coordinates(yandex_geocoder_api_key, client_address)
                if client_coordinates:
                    Place.objects.create(
                        address=client_address,
                        lat=client_coordinates[1],
                        lon=client_coordinates[0],
                    )
                else:
                    client_coordinates = None
            else:
                client_coordinates = [client_place[0].lon, client_place[0].lat]

            if client_coordinates:
                distance_km = round(distance.distance(client_coordinates[::-1], restaurant_coordinates[::-1]).km, 2)
            else:
                distance_km = 'Неправильно указан адрес, None'
            restaurants.append({'restaurant': restaurant, 'distance': distance_km})

        order_items['restaurants'] = restaurants
        orders_with_total_cost.append(order_items)

    return render(request, template_name='order_items.html', context={
        'order_items': orders_with_total_cost,
    })
