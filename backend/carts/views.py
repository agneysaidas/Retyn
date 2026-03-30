from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializer import CartSerializer,CartItemSerializer
from products.models import Product
from users.models import User
from .services import checkout,InsufficientStock

class AddtoCartView(APIView):    
    def post(self,request):
        user = User.objects.first()
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
        user = User.objects.first()
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
        user = User.objects.first()
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
    
class CheckoutView(APIView):
    
    def post(self,request):
        user = User.objects.first()
        cart = Cart.objects.filter(user=user,is_active=True).first()
        
        if not cart:
            return Response(
                {'Error':'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not cart.items.exists():
            return Response(
                {'Error':"Cart has no items"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = checkout(cart)
        except InsufficientStock as e:
            print("CHECKOUT ERROR:",str(e))
            return Response(
                {"error":str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {
                "Message":"Order placed Successfully",
                "order_id":order.id,
                "total_amount":str(order.total_amount),
                "total_discount":str(order.total_discount),
                "final_amount":str(order.final_amount),
            }
        )