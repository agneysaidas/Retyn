from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .services import cancel_order,InvalidOrderState, process_payment,PaymentFailed
from users.models import User
from .serializers import OrderSerializer

class CancelOrderView(APIView):
    def post(self,requst,order_id):
        user = User.objects.first()
        
        try:
            order = Order.objects.get(id = order_id)
        except:
            return Response({"Error":"Order not found"},status=404)
        
        try:
            cancel_order(order,user)
        except InvalidOrderState as e:
            return Response({"Error":str(e)},status=400)
        
        return Response({"Message":"Order cancelled successfully"})
    
class OrderListView(APIView):
    def get(self,request):
        user = User.objects.first()
        
        orders = Order.objects.filter(user=user).order_by('-created_at')
        serializer = OrderSerializer(orders,many=True)
        return Response(serializer.data)
    
class OrderDetailView(APIView):
    def get(self,request,order_id):
        user = User.objects.first()
        
        try:
            order = Order.objects.get(id = order_id)
        except:
            return Response({"Error":"Order not found"},status=404)
        
        #Security check
        if order.user != user:
            return Response({"Error":"Not allowed"},status=403)
        
        serializer = OrderSerializer(order)
        
        return Response(serializer.data)
    
class PaymentView(APIView):
    def post(self,request,order_id):
        user = User.objects.first()
        
        method = request.data.get('method')
        
        if method not in ['Cash','Wallet','Card']:
            return Response({"Error":"Invalid Payment Method"},status=400)
        
        try:
            order = Order.objects.get(id = order_id)
        except Order.DoesNotExist:
            return Response({"Error":"Order not found"},status=404)
        
        if order.user != user:
            return Response({"Error":"Not Allowed"},status=403)
        
        try:
            payment = process_payment(order,method,user)
        except PaymentFailed as e:
            return Response({"Error":str(e)},status=400)
        
        return Response({
            "message":"Payment Successful",
            "order_status":order.status,
            "payment_id":payment.id
        })        