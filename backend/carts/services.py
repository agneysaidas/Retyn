from django.db import transaction,models
from django.utils import timezone
from django.db.models import F,Q
from decimal import Decimal
from products.models import Inventory, Batch,InventoryLog
from orders.models import Order,OrderItem
from offers.models import Offer

class InsufficientStock(Exception):
    pass

def checkout(cart):
    with transaction.atomic():

        total_amount = Decimal('0')      # BEFORE discount
        total_discount = Decimal('0')

        order = Order.objects.create(
            store=cart.store,
            user=cart.user,
            total_amount=0,
            total_discount=0,
            final_amount=0
        )

        #Pre-calculate cart total (IMPORTANT for offers)
        cart_total = Decimal('0')
        for item in cart.items.all():
            price = get_selling_price(item.product)
            batch = Batch.objects.filter(
                product = item.product,
                store = cart.store,
                quantity__gt = 0
            ).order_by('expiry_date').first()
            
            if not batch:
                raise InsufficientStock(f"No stock for {item.product.name}")

            cart_total += batch.selling_price* item.quantity
            
        for item in cart.items.all():
            product = item.product
            quantity_needed = item.quantity

            #Lock rows to prevent race condition
            batches = Batch.objects.select_for_update().filter(
                product=product,
                store=cart.store,
                quantity__gt=0,
                expiry_date__gt=timezone.now()  # ❗ filter expired
            ).order_by('expiry_date')

            if not batches.exists():
                raise InsufficientStock(f"No stock for {product.name}")

            #Get offer ONCE per product
            offer = get_best_offer(
                product=product,
                store=cart.store,
                cart_total=cart_total
            )

            for batch in batches:
                if quantity_needed <= 0:
                    break

                available_qty = batch.quantity
                take_qty = min(batch.quantity, quantity_needed)
                price = get_selling_price(product, batch)

                # 🔹 Base calculations
                base_subtotal = price * take_qty
               
                discount = Decimal('0')

                if offer:
                    if offer.discount_type == 'percentage':
                        discount = base_subtotal * (offer.discount_value / 100)
                    else:
                        discount = offer.discount_value * take_qty

                    if offer.max_discount_value:
                        discount = min(discount, offer.max_discount_value)

                final_subtotal = base_subtotal - discount

                #Save full breakdown
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    batch=batch,
                    quantity=take_qty,
                    price=price,
                    discount = discount,
                    final_price = (price - (discount/take_qty)) if take_qty else price, 
                    subtotal=base_subtotal,   # BEFORE discount
                    final_subtotal = final_subtotal
                )

                #Reduce batch
                batch.quantity = F('quantity') - take_qty
                batch.save()

                #Update inventory directly
                Inventory.objects.filter(
                    product=product,
                    store=cart.store
                ).update(quantity=F('quantity') - take_qty)

                #Log
                InventoryLog.objects.create(
                    store=cart.store,
                    product=product,
                    batch=batch,
                    change=-take_qty,
                    reason='sale',
                    reference_id=order.id
                )

                total_amount += base_subtotal
                total_discount += discount

                quantity_needed -= take_qty

            if quantity_needed > 0:
                raise InsufficientStock(f"Insufficient stock for {product.name}")

            #Increment offer usage (ONCE per product)
            if offer:
                Offer.objects.filter(id = offer.id).update(
                    used_count = F('used_count') +1    
                )
                

        final_amount = total_amount - total_discount

        order.total_amount = total_amount
        order.total_discount = total_discount
        order.final_amount = final_amount
        order.save()

        cart.is_active = False
        cart.save()

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

def get_selling_price(product, batch=None):
    if batch:
        return batch.selling_price