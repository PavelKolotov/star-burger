import json
import phonenumbers

from django.http import JsonResponse
from django.templatetags.static import static
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.response import Response


from .models import Product, Order, OrderItem


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


@api_view(['POST'])
def register_order(request):
    try:
        order_details = request.data
        products = order_details['products']

        if not isinstance(products, list) or not len(products):
            return Response({'error': 'Products key not presented or not list'},
                            status=400)

        required_keys = ['firstname', 'lastname', 'address', 'phonenumber']
        for key in required_keys:
            value = order_details.get(key)
            if not value or not isinstance(value, str):
                return Response({'error': f'Order {key} not presented or not string'}, status=400)

        parsed_number = phonenumbers.parse(order_details['phonenumber'], "RU")
        if not phonenumbers.is_valid_number(parsed_number) \
            and not phonenumbers.region_code_for_number(parsed_number) == "RU":
            return Response({'error': 'Phonenumbers is not valid'},
                            status=400)

        for product in products:
            product_id = product['product']
            quantity = product['quantity']

            try:
                product_obj = Product.objects.get(id=product_id)
            except ObjectDoesNotExist:
                return Response({'error': f'Product with ID {product_id} does not exis'},
                                status=400)

            order = Order.objects.create(
                firstname=order_details['firstname'],
                lastname=order_details['lastname'],
                address=order_details['address'],
                phonenumber=order_details['phonenumber'])

            OrderItem.objects.create(
                order=order,
                product=product_obj,
                quantity=quantity
            )
            return Response({'message': 'Order created successfully'})


    except (json.JSONDecodeError, KeyError) as e:
        return Response({'error': str(e)}, status=400)

    except phonenumbers.phonenumberutil.NumberParseException:
        return Response({'error': 'Phonenumbers is not valid'}, status=400)
