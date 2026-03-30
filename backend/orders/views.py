from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .services import cancel_order,InvalidOrderState
from users.models import User

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