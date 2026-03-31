from django.db import transaction,models
from django.utils import timezone
from django.db.models import F,Q
from decimal import Decimal
from products.models import Inventory, Batch,InventoryLog
from orders.models import Order,OrderItem
from offers.models import Offer
import logging

logger = logging.getLogger(__name__)

class InsufficientStock(Exception):
    pass

def checkout(cart):
    logger.info(f"Checkout started for Cart {cart.id}")
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
            # price = get_selling_price(item.product)
            batches = Batch.objects.filter(
                product = item.product,
                store = cart.store,
                quantity__gt = 0,
                expiry_date__gt = timezone.now()
            ).order_by('expiry_date')
            
            if not batches.exists():
                logger.error(f"No stock for product {item.product.id}")
                raise InsufficientStock(f"No stock for {item.product.name}")
            
            qty_needed = item.quantity
            
            for batch in batches:
                if qty_needed <= 0:
                    break
                
                take = min(batch.quantity,qty_needed)
                cart_total += batch.selling_price* take
                qty_needed -= take
                
            if qty_needed>0:
                logger.error(f"Insufficient stock for product {item.product.id}")
                raise InsufficientStock(f"Insufficient stock for product {item.product.id}")
         
        #MAIN Processing   
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
            
            #Get offer ONCE per product
            offer = get_best_offer(
                product=product,
                store=cart.store,
                cart_total=cart_total
            )
            
            logger.info(f"Processing product {product.id} with offer {offer.id if offer else None}")

            for batch in batches:
                if quantity_needed <= 0:
                    break

                take_qty = min(batch.quantity, quantity_needed)
                price = batch.selling_price

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
                    store=cart.store,
                    batch = batch,
                    change = -take_qty,
                    reason = 'SALE'
                )
                
                logger.info(f"Deducted {take_qty} from batch {batch.ig}")

                total_amount += base_subtotal
                total_discount += discount

                quantity_needed -= take_qty

            if quantity_needed > 0:
                logger.error(f"Stock mismatch during checkout for product {product.id}")
                raise InsufficientStock(f"Insufficient stock for {product.name}")
            
            #Update inventory ONCE per product
            total_qty = Batch.objects.filter(
                product=product,
                store = cart.store
            ).aggregate(total = models.Sum('quantity'))['total'] or 0
            
            Inventory.objects.filter(
                product = product,
                store = cart.store 
            ).update(quantity = total_qty)

            #Increment offer usage (ONCE per product)
            if offer:
                Offer.objects.filter(id = offer.id).update(
                    used_count = F('used_count') +1    
                )
                logger.info(f"Offer {offer.id} used for product {product.id}")

        final_amount = total_amount - total_discount

        order.total_amount = total_amount
        order.total_discount = total_discount
        order.final_amount = final_amount
        order.save()

        cart.is_active = False
        cart.save()
        
        logger.info(f"Checkout completed for Cart {cart.id}, Order {order.id}")

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
