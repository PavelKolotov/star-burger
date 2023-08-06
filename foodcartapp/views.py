import requests

from django.http import JsonResponse
from django.templatetags.static import static
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response

from geopy import distance
from environs import Env

from .serializers import OrderSerializer
from .models import Product
from place.models import Place


def create_place(address):
    env = Env()
    env.read_env()
    yandex_geocoder_api_key = env.str('YANDEX_GEOCODER_API_KEY')
    place = Place.objects.filter(address=address)
    if not place:
        coordinates = fetch_coordinates(yandex_geocoder_api_key, address)
        if coordinates:
            Place.objects.create(
                address=address,
                lat=coordinates[1],
                lon=coordinates[0],
            )
        else:
            Place.objects.create(
                address=address,
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


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@transaction.atomic
@api_view(['POST'])
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    order = serializer.save()
    serialized_order = OrderSerializer(order).data
    create_place(serialized_order['address'])

    return Response(serialized_order)

