from django.db import transaction,models
from .models import Order
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