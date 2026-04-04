from decimal import Decimal
import random
import razorpay
from django.db import transaction,models
from django.db.models import F
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from orders.models import Order,Payment,PaymentAuditLog
from products.models import Inventory,Batch,InventoryLog
import logging
from core.locks import SafeLock

logger = logging.getLogger(__name__)
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class InvalidOrderState(Exception):
    pass
    
class PaymentFailed(Exception):
    pass

class Lock:
    def init(self, key, ttl=10):
        self.key = key
        self.ttl = ttl

    def acquire(self):
        return cache.add(self.key, "1", self.ttl)

    def release(self):
        cache.delete(self.key)

def fraud_check(user, request):

    ip = request.META.get("REMOTE_ADDR")

    window = timezone.now() - timedelta(minutes=10)

    # 🔒 Too many attempts in short time
    if Payment.objects.filter(
        user=user,
        created_at__gte=window
    ).count() > 5:
        return False

    # 🔒 Too many from same IP
    if Payment.objects.filter(
        ip_address=ip,
        created_at__gte=window
    ).count() > 10:
        return False

    return True

def handle_cod(order):
    logger.info(f"Processing CASH payment for Order {order.id}")
    payment = Payment.objects.create(
        order = order,
        method = "CASH",
        amount= order.final_amount,
        status = "SUCCESS"
    )
    
    confirm_order(order)
    
    return payment

def handle_wallet(order,user):
    logger.info(f"Processing WALLET payment for Order {order.id}")
    #simulate wallet balance
    wallet_balance = Decimal('500')
    
    if wallet_balance < order.final_amount:
        logger.warning(f"Insufficient wallet balance for Order {order.id}")
        payment = Payment.objects.create(
            order = order,
            method = "WALLET",
            amount= order.final_amount,
            status = "FAILED"
        )
        raise PaymentFailed("Insufficient wallet balance")
    
    payment = Payment.objects.create(
        order = order,
        method = "WALLET",
        amount= order.final_amount,
        status = "SUCCESS"
    )
    
    confirm_order(order)
    
    return payment

def handle_card(order):
    logger.info(f"Processing CARD payment for Order {order.id}")
    success = random.choice([True,False])
    
    if not success:
        logger.error(f"Card payment failed for Order {order.id}")
        payment = Payment.objects.create(
            order = order,
            method = "CARD",
            amount= order.final_amount,
            status = "FAILED"
        )
        raise PaymentFailed("Card Payment Failed")
    
    payment = Payment.objects.create(
        order = order,
        method = "CARD",
        amount= order.final_amount,
        status = "SUCCESS"
    )
    
    confirm_order(order)
    
    return payment

def process_payment(order, method, user):

    lock = Lock(f"payment:{order.id}")
    if not lock.acquire():
        raise Exception("Payment in progress")

    try:
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "method": method,
                "amount": order.final_amount,
                "status": "PENDING",
                "user": user
            }
        )

        PaymentAuditLog.objects.create(
            payment=payment,
            event="INITIATED"
        )

        return payment

    finally:
        lock.release()
    
def create_payment_order(request,user,order):
    
    lock = SafeLock(f"order_payment_{order.id}",ttl=15)
    if not lock.acquire():
        raise Exception("Payment already in Progress")
    if not fraud_check(user,request):
        raise Exception("Suspicious activity detected")
    logger.info(f"Creating Razorpay order for Order{order.id}")
    try:
        if order.status != 'PENDING':
            logger.warning(f"Invalid Razorpay request for Order {order.id}")
            raise Exception("Invalid order state")
        
        amount = int(order.final_amount * 100)
        
        razorpay_order = client.order.create({
            'amount':amount,
            'currency':"EUR",
            'payment_capture':1
        })
        
        payment = Payment.objects.create(
            order= order,
            method = 'CARD',
            amount = order.final_amount,
            status = "PENDING",
            razorpay_order_id = razorpay_order['id']
        )
        logger.info (f"Razorpay order created for Order {order.id}")
        
        return{
            'razorpay_order_id': razorpay_order['id'],
            'amount':amount
        }
    finally:
        lock.release()

def cancel_order(order,user=None):
    logger.info(f"Cancel request for Order {order.id}")
    with transaction.atomic():
        
        order = Order.objects.select_for_update().get(id = order.id)
        
        if order.staus != "PENDING":
            logger.warning(f"Order {order.id} already proccessed")
            return Order
        
        #Ownership check(only if user-triggered)
        if user and order.user != user:
            logger.warning(f"Unauthorized cancel attempt for Order{order.id}")
            raise InvalidOrderState("Not allowed")
        
        #Prevent duplicate cancel
        if order.status == "CANCELLED":
            logger.warning(f"Duplicate cancel attempt for order {order.id}")
            raise InvalidOrderState("Order already canelled")
        
        #Restore stock
        for item in order.items.all():
            batch = item.batch
            
            #Restore batch quanity safely
            batch.quantity = models.F('reserved_quantity') - item.quantity
            batch.save()
            
            #Inventory Log
            InventoryLog.objects.create(
                store = order.store,
                product = item.product,
                batch=batch,
                change = item.quantity,
                reason = 'CANCEL',
                reference_id = order.id
            )
            
            logger.info(f"Restored {item.quantity} units for product {item.product.id}")
            
        #Update inventory ONCE per product (not loop twicw)
        product_ids = set(order.items.values_list('product_id', flat = True))
        
        for product_id in product_ids:
            total_qty = Batch.objects.filter(
                product_id = product_id,
                store = order.store
            ).aggregate(total = models.Sum('quantity'))['total'] or 0
            
            Inventory.objects.filter(
                product_id = product_id,
                store = order.store
            ).update(quantity = total_qty)
            
        #Update order status
        order.status = "CANCELLED"
        order.save()
        
        logger.info (f"Order {order.id} cancelled successfully")
        
        return order        
    
def confirm_order(order):
    with transaction.atomic():

        if order.status == "CONFIRMED":
            return order

        if order.status != "PENDING":
            raise Exception("Invalid state")

        for item in order.items.select_related("batch"):

            batch = item.batch

            batch.quantity = F("quantity") - item.quantity
            batch.reserved_quantity = F("reserved_quantity") - item.quantity
            batch.save()

        order.status = "CONFIRMED"
        order.save()

        return order