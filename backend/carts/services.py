from django.db import transaction,models
from django.utils import timezone
from django.db.models import F,Q
from decimal import Decimal
from products.models import Inventory, Batch,InventoryLog
from orders.models import Order,OrderItem
from offers.models import Offer

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
        
        #Loop through cart items        
        for item in carts.items.all():
            product = item.product
            quantity_needed = item.quantity
            
            #Get batched sorted by expiry(FIFO)
            batches = Batch.objects.filter(
                product = product,
                store = carts.store,
                quantity__gt = 0
            ).order_by('expiry_date')
        
            if not batches.exists():
                raise Exception(f"No stock for {product.name}")
        
            #Process each batch
            for batch in batches:
                if quantity_needed <= 0:
                    break
                
                available_qty = batch.quantity
                take_qty = min(available_qty,quantity_needed)
                price= batch.selling_price
            
                offer = get_best_offer(product=product,store=carts.store,cart_total=price*quantity_needed)
            
                discount_per_unit = Decimal('0')
            
                if offer:
                    if offer.discount_type == 'percentage':
                        discount_per_unit = price*(offer.discount_value/100)
                    else:
                        discount_per_unit= offer.discount_value
                    #Apply max cap
                    if offer.max_discount_value:
                        discount_per_unit = min(discount_per_unit,offer.max_discount_value)
                
                final_price = price - discount_per_unit
                #Total per item
                subtotal = final_price*take_qty
            
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    batch = batch,
                    quantity=take_qty,
                    price= price,
                    subtotal = subtotal
                )   
            
                #Reduce batch quantity
                batch.quantity -= take_qty
                batch.save()
            
                InventoryLog.objects.create(
                    store=carts.store,
                    product = product,
                    batch=batch,
                    change = -take_qty,
                    reason='sale',
                    reference_id = order.id
                )
            
                total_amount += subtotal
                total_discount += discount_per_unit * take_qty
                quantity_needed -= take_qty
            
            if quantity_needed>0:
                raise Exception(f"Insufficient Stock for{product.name}")
        
            inventory = Inventory.objects.get(
                product=product,
                store = carts.store
            )
  
            total_batch_quantity = Batch.objects.filter(
                product = product,
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

def get_best_offer(product,store,cart_total):
    now = timezone.now()
    current_day = now.weekday()    

    offers = Offer.objects.filter(
        is_active = True,
        start_date__lte = now,
        end_date__gte = now,
        min_cart_value__lte = cart_total
    )
    
    #Filter product-speciffic offers
    offers = offers.filter(
        Q(usage_limit__isnull = True)|Q(usage_limit__gt = F('used_count'))
    )
    
    #Apply cart condition
    offers = offers.filter(
        Q(offerproduct__product = product)|
        Q(offercategory__category = product.category)|
        Q(offerstore__store = store)|
        Q(offerday__day_of_week = current_day)
    ).distinct()
    
    #Pick highest Priority
    return offers.order_by('-priority').first()