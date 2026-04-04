from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
import razorpay
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
from .models import Order, Payment
from .services import cancel_order,InvalidOrderState, process_payment,PaymentFailed,create_payment_order
from users.models import User
from .serializers import OrderSerializer, CheckoutSerializer

def checkout(request):
    serializer = CheckoutSerializer(data = request.headers)
    serializer.is_valid(raise_exception = True)
    
    idempotency_key = serializer.validated_data['idempotency_key']
    
    create_payment_order(request.user,idempotency_key)
    
    return Response({"status":"ok"},status = status.HTTP_200_OK)

class OrderListView(APIView):
    def get(self,request):
        user = request.user
        orders = Order.objects.filter(user = user).order_by('-created_at')
        serializer = OrderSerializer(orders,many = True)
        return Response(serializer.data)
    
class OrderDetailView(APIView):
    def get(self,request,order_id):
        
        order = Order.objects.filter(
            id = order_id,
            user = request.user
        ).first()
        
        if not order:
            return Response({"Error":"Order not found"},status=404)
        
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    
class PaymentView(APIView):
    def post(self,request,order_id):
        
        method = request.data.get('method')
        
        if method not in ['CASH','WALLET','CARD']:
            return Response({"Error":"Invalid Payment Method"},status=400)

        order = Order.objects.filter(
            id = order_id,
            user = request.user
        ).first()
        if not order:
            return Response({"Error":"Order not found"},status=404)
        
        try:
            payment = process_payment(order,method,request.user)
        except PaymentFailed as e:
            return Response({"Error":str(e)},status=400)
        
        return Response({
            "success":True,
            "order_status":order.status,
            "payment_id":payment.id
        })   
        
class CreatePaymentView(APIView):
    def post(self,request,order_id):
        
        order = Order.objects.filter(
            id = order_id,
            user = request.user
        ).first()
        
        if not order:
            return Response({"Error":"Order not found"},status=404)
        
        data = create_payment_order(order)   
        return Response({"success":True,"data":data})  
    
@csrf_exempt
def razorpay_webhook(request):
    body = request.body
    signature = request.headers.get('X-Razorpay-Signature')
    
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
    
    try:
        client.utility.verify_webhook_signature(
            body, 
            signature, 
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except:
        return HttpResponse(status=400)
    
    data = json.loads(body)
    event = data.get('event')
    
    #Extract data safely
    payload = data.get('payload',{})
    payment_entity = payload.get('payment',{}).get('entity',{})
    
    razorpay_order_id = payment_entity.get('order_id')
    razorpay_payment_id = payment_entity.get('id')
    
    if not razorpay_order_id:
        return HttpResponse(status=400)
    
    try:
        payment = Payment.objects.select_for_update().get(
            razorpay_order_id = razorpay_order_id
        )
    except Payment.DoesNotExist:
        return HttpResponse(status=404)
    
    #Idempotency check
    if payment.status in ['SUCCESS','FAILED']:
        return HttpResponse(status = 200)
    
    with transaction.atomic():
        
        order = payment.order
        if event == 'payment.captured':
            payment.status = "SUCCESS"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save()
    
            #prevent double confirmation
            if order.status != 'CONFIRMED':
                order.status = 'CONFIRMED'
                order.save()
        elif event == 'payment.failed':
            payment.status = 'FAILED'
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save()
            
            cancel_order(order)
        
    return HttpResponse(status=200)

class CancelOrderView(APIView):
    def post(self,request,order_id):
        
        order = Order.objects.filter(
            id = order_id,
            user = request.user
        ).first()
        
        if not order:
            return Response({"Error":"Order not found"},status=404)
    
        try:
            cancel_order(order,request.user)
        except InvalidOrderState as e:
            return Response({"Error":str(e)},status=400)
        
        return Response({"success":True,"Message":"Order cancelled successfully"})