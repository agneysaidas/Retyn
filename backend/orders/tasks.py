from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Order,Payment
from .services import cancel_order,confirm_order
import logging
from django.db.models import F
from django.db import transaction

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={'max_retries': 3})
def expire_orders(self):

    expiry = timezone.now() - timedelta(minutes=15)

    with transaction.atomic():
        orders = Order.objects.select_for_update(skip_locked=True).filter(
            status="PENDING",
            created_at__lt=expiry
        )

        for order in orders:

            for item in order.items.select_related("batch"):
                batch = item.batch
                batch.reserved_quantity = F("reserved_quantity") - item.quantity
                batch.save()

            order.status = "CANCELLED"
            order.save()

@shared_task(bind=True,autoretry_for=(Exception,),retry_backoff=5,max_reties = 3)
def handle_payment_success(self, razorpay_order_id):
    try:
        with transaction.atomic():

            # 🔴 LOCK payment row
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )

            order = payment.order

            # ✅ Idempotency check
            if payment.status == "SUCCESS":
                logger.info(f"Payment already processed for Order {order.id}")
                return

            logger.info(f"Processing payment for Order {order.id}")

            # ✅ Mark payment success
            payment.status = "SUCCESS"
            payment.save()

            # ✅ Confirm order safely
            confirm_order(order)

            logger.info(f"Order {order.id} CONFIRMED successfully")

    except Payment.DoesNotExist:
        logger.error(f"Payment not found for razorpay_order_id {razorpay_order_id}")

    except Exception as e:
        payment.status='FAILED',
        payment.last_attempt_at = timezone.now()
        payment.retry_count = F('retry_count')+1
        payment.save()
        logger.error(f"Error processing payment: {str(e)}")
        raise self.retry(exc=e)
    
@shared_task
def retry_failed_payment():
    retry_window = timezone.now() - timedelta(minutes = 5)
    failed_payments = Payment.objects.filter(
        status = "FAILED",
        retry_count__lt = 5,
        last_attempt_at__lt = retry_window
    )
    for payment in failed_payments:
        try:
            with transaction.atomic():

                # 🔒 Lock row
                payment = Payment.objects.select_for_update().get(id=payment.id)

                # ✅ Skip if already fixed
                if payment.status == "SUCCESS":
                    continue

                # ✅ Mark retry attempt
                payment.retry_count = F("retry_count") + 1
                payment.last_attempt_at = timezone.now()
                payment.status = "PENDING"  # or "RETRYING" if you add it
                payment.save()

            # 🚀 Trigger async task OUTSIDE transaction
            handle_payment_success.delay(payment.razorpay_order_id)

        except Exception as e:
            logger.error(f"Retry failed for payment {payment.id}: {str(e)}")
    
    