from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from .models import Cart, CartItem
from .serializer import CartSerializer,CartItemSerializer,CheckoutSerializer
from products.models import Product
from users.models import User
from .services import checkout,InsufficientStock

class AddtoCartView(APIView):    
    def post(self,request):
        user = request.user
        product_id = request.data.get('product')
        quantity = request.data.get('quantity',1)
        
        if quantity <= 0:
            return Response({'Error':'Quantity must be >0'},status=400)
        
        product = Product.objects.get(id = product_id)
        
        #Get or create active cart
        cart,created = Cart.objects.get_or_create(
            user = user,
            store = user.store,
            is_active = True
        )
        
        #check if item already exists
        cart_item,created = CartItem.objects.get_or_create(
            cart=cart,
            product = product,
            defaults={'quantity':quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
            
        return Response ({"message":"Item added to cart"})
    
class CartView(APIView):
    def get(self,request):
        user = request.user
        try:
            cart = Cart.objects.get(user=user,is_active = True)
        except Cart.DoesNotExist:
            return Response({"message":"Cart is empty"})
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
class UpdateCartItemView(APIView):
    
    def patch(self,request):
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity'))
        
        if quantity <=0 :
            return Response({'error':'Quantity must be >0'},status=400)
        
        item = CartItem.objects.get(id = item_id)
        item.quantity = quantity
        item.save()
        
        return Response({'Message':"Cart Updated."})
    
class RemoveCartItemView(APIView):
    
    def delete(self,request):
        user = request.user
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response({"Error":"Item_id is required"},status=400)
        
        try:
            item = CartItem.objects.get(id = item_id)
        except CartItem.DoesNotExist:
            return Response({"Error":"Item not Found"},status=400)

        if item.cart.user != user:
            return Response({'Error':"Not Allowed"},status=400)
        
        item.delete()
        
        return Response({'Message':"Item removed"})
    
def rate_limit(request):
    key = f"rate:{request.user.id}:{request.META.get('REMOTE_ADDR')}"
    count = cache.get(key, 0)

    if count > 30:
        return False

    cache.set(key, count + 1, timeout=60)
    return True


class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data={
            "idempotency_key": request.headers.get("Idempotency-Key")
        })

        serializer.is_valid(raise_exception=True)

        key = serializer.validated_data["idempotency_key"]
        
        if not key:
            return Response({"error": "Missing key"}, status=400)

        if not rate_limit(request):
            return Response({"error": "Too many requests"}, status=429)

        cart = Cart.objects.filter(user=request.user, is_active=True).first()

        if not cart or not cart.items.exists():
            return Response({"error": "Empty cart"}, status=400)

        order = checkout(cart, key)

        return Response({
            "order_id": order.id,
            "amount": str(order.final_amount)
        })
