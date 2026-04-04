from rest_framework import serializers
from orders.models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source = 'product.name')
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'quantity',
            'price',
            'subtotal',
        ]
        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many = True, read_only =True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'store',
            'status',
            'total_amount',
            'total_discount',
            'final_amount',
            'created_at',
            'items',
        ]
        
class CheckoutSerializer(serializers.ModelSerializer):
    idempotency_key = serializers.CharField(
        max_length = 255,
        required = True,
        allow_blank = False,
        trim_whitespace = True
    )