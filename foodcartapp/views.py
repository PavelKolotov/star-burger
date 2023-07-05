import json

from django.http import JsonResponse
from django.templatetags.static import static
from django.core.exceptions import ObjectDoesNotExist


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


def register_order(request):
    try:
        order_details = json.loads(request.body.decode())

        order = Order.objects.create(
            firstname=order_details['firstname'],
            lastname=order_details['lastname'],
            address=order_details['address'],
            phonenumber=order_details['phonenumber'])

        products = order_details['products']

        for product in products:
            product_id = product['product']
            quantity = product['quantity']

            try:
                product_obj = Product.objects.get(id=product_id)
            except ObjectDoesNotExist:
                raise ValueError(f"Product with ID {product_id} does not exist")

            OrderItem.objects.create(
                order=order,
                product=product_obj,
                quantity=quantity
            )

        return {
            'success': True,
            'order_id': order.id
        }
    except json.JSONDecodeError as e:
        return {'success': False, 'error': 'Invalid JSON format'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

