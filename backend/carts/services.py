from django.db import transaction, IntegrityError
from django.db.models import F,Q
from django.utils import timezone
from decimal import Decimal
from django.core.cache import cache
from django_redis import get_redis_connection
from products.models import Batch
from orders.models import Order, OrderItem
from offers.models import Offer, OfferUsage

class InsufficientStock(Exception):
    pass


class Lock:
    def init(self, key, ttl=15):
        self.key = key
        self.ttl = ttl

    def acquire(self):
        return cache.add(self.key, "1", self.ttl)

    def release(self):
        cache.delete(self.key)


def checkout(cart, idempotency_key):
    redis_conn = get_redis_connection("default")
    lock = redis_conn.lock(f"checkout:{cart.id}", timeout=10)

    acquired = lock.acquire(blocking=False)
    if not acquired:
        raise Exception("Checkout in progress")

    try:
        with transaction.atomic():

            existing_order = Order.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing_order:
                return existing_order

            total = Decimal("0")
            discount_total = Decimal("0")
            
            order = Order.objects.create(
                user=cart.user,
                store=cart.store,
                status="PENDING",
                idempotency_key=idempotency_key,
                total_amount=Decimal("0"),
                total_discount=Decimal("0"),
                final_amount=Decimal("0"),
            )


            for item in cart.items.select_related("product"):

                qty = item.quantity

                batches = Batch.objects.select_for_update(skip_locked=True).filter(
                    product=item.product,
                    store=cart.store,
                    quantity__gt=F("reserved_quantity"),
                    expiry_date__gt=timezone.now()
                ).order_by("expiry_date")

                if not batches:
                    raise InsufficientStock(item.product.name)

                offer = get_best_offer(item.product, cart.store, total)

                for batch in batches:
                    if qty <= 0:
                        break

                    available = batch.quantity - batch.reserved_quantity
                    take = min(qty, available)

                    updated = Batch.objects.filter(
                        id=batch.id,
                        reserved_quantity__lte=F("quantity") - take
                    ).update(
                        reserved_quantity=F("reserved_quantity") + take
                    )

                    if not updated:
                        continue

                    price = batch.selling_price
                    subtotal = price * take
                    

                    discount = Decimal("0")
                    if offer:
                        discount = calculate_discount(offer, subtotal, take)

                    final_subtotal = subtotal - discount
                    final_price = final_subtotal / take
                    
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        batch=batch,
                        quantity=take,
                        price=price,
                        discount=discount,
                        subtotal=subtotal,
                        final_subtotal=final_subtotal,
                        final_price = final_price
                    )

                    total += subtotal
                    discount_total += discount
                    qty -= take

                if qty > 0:
                    raise InsufficientStock(item.product.name)

                if offer:
                    try:
                        OfferUsage.objects.create(
                            user=cart.user,
                            offer=offer,
                            order=order
                        )
                    except IntegrityError:
                        pass  # safe

            order.total_amount = total
            order.total_discount = discount_total
            order.final_amount = total - discount_total
            order.save(update_fields=[
                "total_amount",
                "total_discount",
                "final_amount"
            ])

            cart.is_active = False
            cart.save()

            return order

    finally:
        if acquired:
            lock.release()


def calculate_discount(offer, subtotal, qty):
    if offer.discount_type == "percentage":
        return subtotal * (offer.discount_value / 100)
    return offer.discount_value * qty

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
