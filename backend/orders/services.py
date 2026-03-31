from decimal import Decimal
import random
import razorpay
from django.db import transaction,models
from orders.models import Order,Payment
from products.models import Inventory,Batch,InventoryLog
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class InvalidOrderState(Exception):
    pass
    
class PaymentFailed(Exception):
    pass

def handle_cod(order):
    logger.info(f"Processing CASH payment for Order {order.id}")
    payment = Payment.objects.create(
        order = order,
        method = "CASH",
        amount= order.final_amount,
        status = "SUCCESS"
    )
    order.status = "CONFIRMED"
    order.save()
    logger.info(f"Order {order.id} confirmed via CASH")
    
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
    
    order.status = "CONFIRMED"
    order.save()
    logger.info(f"Order {order.id} confirmed via WALLET")
    
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
    
    order.status = "CONFIRMED"
    order.save()
    logger.info(f"Order {order.id} confirmed via CARD")
    
    return payment

def process_payment(order,method,user = None):
    logger.info(f"Starting payment for Order {order.id} with method {method}")
    if order.status!= 'pending':
        logger.warning(f"Invalid payment attempt for Order {order.id}")
        raise PaymentFailed("Invalid order state")
    
    #COD always succeeds
    if method == "CASH":
        return handle_cod(order)
    elif method == "WALLET":
        return handle_wallet(order,user)
    elif method == "CARD":
        return handle_card(order)
    else:
        logger.error(f"Invalid payment method {method} for Order {order.id}")
        raise PaymentFailed("Invalid Payment Method")
    
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_payment_order(order):
    logger.info(f"Creating Razorpay order for Order{order.id}")
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
    
class InvalidOrderState(Exception):
    pass

def cancel_order(order,user=None):
    logger.info(f"Cancel request for Order {order.id}")
    with transaction.atomic():
        
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
            batch.quantity = models.F('quantity')+item.quantity
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
            
            