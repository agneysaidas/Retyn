from django.db import transaction,models
from decimal import Decimal
from products.models import Inventory, Batch
from orders.models import Order,OrderItem

def checkout(carts):
    with transaction.atomic():
        total_amount = Decimal('0')
        total_discount = Decimal('0')
        
        order = Order.objects.create(
            store = carts.store,
            user = carts.user,
            total_amount = 0,
            total_discount = 0,
            final_amount=0
        )
        
        for item in carts.items.all():
            quantity_needed = item.quantity
            
            #Get batched sorted by expiry(FIFO)
            batches = Batch.objects.filter(
                product = item.product,
                store = carts.store,
                quantity__gt = 0
            ).order_by('expiry_date')
        
        if not batches.exists():
            raise Exception(f"No stock for {item.product.name}")
        
        for batch in batches:
            if quantity_needed <= 0:
                break
                
            available_qty = batch.quantity
            take_qty = min(available_qty,quantity_needed)
            price= batch.selling_price
            subtotal = price*take_qty
            
            #Create OrderItem PER BATCH
            OrderItem.objects.create(
                order=order,
                product=item.product,
                batch=batch,
                quantity = take_qty,
                price=price,
                subtotal=subtotal
            )
            
            #Reduce batch quantity
            batch.quantity -= take_qty
            batch.save()
            
            total_amount += subtotal
            quantity_needed -= take_qty
            
        if quantity_needed>0:
            raise Exception(f"Insufficient Stock for{item.product.name}")
            
        #Update Inventory
        for item in carts.items.all():
            inventory = Inventory.objects.get(
                product = item.product,
                store=carts.store
            )
                
            total_batch_quantity = Batch.objects.filter(
                product = item.product,
                store = carts.store
            ).aggregate(total=models.Sum('quantity'))['total'] or 0
            
            inventory.quantity = total_batch_quantity
            inventory.save()
        
        final_amount = total_amount-total_discount
        
        order.total_amount = total_amount
        order.total_discount = total_discount
        order.final_amount = final_amount
        order.save()
        
        carts.is_active = False
        carts.save()
        
        return order