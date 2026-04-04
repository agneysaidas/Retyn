from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
from rest_framework.permissions import AllowAny
from django.db import IntegrityError,transaction
from .tasks import handle_payment_success
from .models import Payment,PaymentAuditLog,PaymentWebhookLog
import razorpay
import json
import logging


logger = logging.getLogger(__name__)
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@api_view(["POST"])
@permission_classes([AllowAny])
def payment_webhook(request):

    payload = request.body
    signature = request.headers.get("X-Razorpay-Signature")

    try:
        client.utility.verify_webhook_signature(
            payload,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except:
        return Response(status=400)

    data = json.loads(payload)

    if data.get("event") != "payment.captured":
        return Response({"ignored": True})
    
    event_id = data.get("id")
    
    try:
        with transaction.atomic():
            PaymentWebhookLog.objects.create(event_id = event_id)
    except IntegrityError:
        return Response({'status':"dupliacate"})
        

    entity = data["payload"]["payment"]["entity"]
    order_id = entity["order_id"]

    payment = Payment.objects.filter(
        razorpay_order_id=order_id
    ).first()

    if not payment:
        return Response(status=404)

    PaymentAuditLog.objects.create(
        payment=payment,
        event="WEBHOOK_RECEIVED"
    )

    handle_payment_success.delay(order_id)

    return Response({"ok": True})