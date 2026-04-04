from rest_framework import serializers
from .models import Cart, CartItem
from products.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source = 'product.name',read_only=True)
    class Meta:
        model = CartItem
        fields = ['id','product','product_name','quantity']
        
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True,read_only = True)
    class Meta:
        model = Cart
        fields = ['id','store','user','items']
        
class CheckoutSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(
        max_length = 255,
        required = True,
        allow_blank = False,
        trim_whitespace = True
    )