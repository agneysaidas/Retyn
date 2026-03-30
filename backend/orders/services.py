from decimal import Decimal
import random

from django.db import transaction,models
from orders.models import Order,Payment
from products.models import Inventory,Batch,InventoryLog

class InvalidOrderState(Exception):
    pass

def cancel_order(order,user):
    with transaction.atomic():
        
        #Validate Ownership
        if order.user != user:
            raise InvalidOrderState("Not Allowed")
        
        #Prevent double cancel
        if order.status == "cacelled":
            raise InvalidOrderState("Order already Cancelled")
        
        #Restore Stock
        for item in order.items.all():
            batch = item.batch
            
            #Restore Batch quantity
            batch.quantity = models.F('quantity')+item.quantity
            batch.save()
            
            #Log inventory
            InventoryLog.objects.create(
                store= order.store,
                product = item.product,
                batch = batch,
                change = item.quantity,
                reason="cancel",
                reference_id = order.id
            )
            
        #Recalculate Inventory
        for item in order.items.all():
            
            total_qty = Batch.objects.filter(
                product = item.product,
                store = order.store
            ).aggregate(total = models.Sum('quantity'))['total'] or 0
            
            Inventory.objects.filter(
                product = item.product,
                store = order.store
            ).update(quantity = total_qty)
            
        #Update Status
        order.status = 'Cancelled'
        order.save()
        
        return order
    
class PaymentFailed(Exception):
    pass

def handle_cod(order):
    payment = Payment.objects.create(
        order = order,
        method = "Cash",
        amount= order.final_amount,
        status = "Success"
    )
    order.status = "Confirmed"
    order.save()
    
    return payment

def handle_wallet(order,user):
    #simulate wallet balance
    wallet_balance = Decimal('500')
    
    if wallet_balance < order.final_amount:
        payment = Payment.objects.create(
            order = order,
            method = "Wallet",
            amount= order.final_amount,
            status = "Failed"
        )
        raise PaymentFailed("Insufficient wallet balance")
    
    payment = Payment.objects.create(
        order = order,
        method = "Wallet",
        amount= order.final_amount,
        status = "Success"
    )
    
    order.status = "Confirmed"
    order.save()
    
    return payment

def handle_card(order):
    success = random.choice([True,False])
    
    if not success:
        payment = Payment.objects.create(
            order = order,
            method = "Card",
            amount= order.final_amount,
            status = "Failed"
        )
        raise PaymentFailed("Card Payment Failed")
    
    payment = Payment.objects.create(
        order = order,
        method = "Card",
        amount= order.final_amount,
        status = "Success"
    )
    
    order.status = "Confirmed"
    order.save()
    
    return payment

def process_payment(order,method,user = None):
    if order.status!= 'pending':
        raise PaymentFailed("Invalid order state")
    
    #COD always succeeds
    if method == "Cash":
        return handle_cod(order)
    elif method == "Wallet":
        return handle_wallet(order,user)
    elif method == "Card":
        return handle_card(order)
    else:
        raise PaymentFailed("Invalid Payment Method")
    