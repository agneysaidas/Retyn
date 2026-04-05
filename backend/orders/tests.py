from django.test import TestCase
from rest_framework.test import APIClient
from orders.models import Order
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentFlowTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password"
        )
        self.client.force_authenticate(user=self.user)

    def test_payment_success_flow(self):
        # Step 1: Create order
        response = self.client.post("/orders/create/", {
            "items": [
                {"product_id": 1, "quantity": 2}
            ]
        }, format="json")

        self.assertEqual(response.status_code, 201)

        order_id = response.data["id"]

        # Step 2: Simulate payment success webhook
        webhook_payload = {
            "razorpay_payment_id": "pay_123",
            "order_id": order_id,
            "status": "success"
        }

        response = self.client.post("/payments/webhook/", webhook_payload)

        self.assertEqual(response.status_code, 200)

        # Step 3: Verify order updated
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, "PAID")
        
class IdempotencyTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test2@example.com",
            password="password"
        )
        self.client.force_authenticate(user=self.user)

    def test_idempotent_checkout(self):
        headers = {
            "HTTP_IDEMPOTENCY_KEY": "unique-key-123"
        }

        payload = {
            "items": [
                {"product_id": 1, "quantity": 1}
            ]
        }

        # First request
        response1 = self.client.post("/checkout/", payload, format="json", **headers)

        # Second request (same key)
        response2 = self.client.post("/checkout/", payload, format="json", **headers)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # 🔥 CRITICAL: Only one order should exist
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)

        # Optional: same response
        self.assertEqual(response1.data, response2.data)
        
class DuplicatePaymentTest(TestCase):

    def test_duplicate_payment_blocked(self):
        from .models import Payment

        Payment.objects.create(
            razorpay_payment_id="pay_123",
            amount=100
        )

        with self.assertRaises(Exception):
            Payment.objects.create(
                razorpay_payment_id="pay_123",
                amount=100
            )
            
class WebhookIdempotencyTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_webhook_duplicate(self):
        payload = {
            "razorpay_payment_id": "pay_456",
            "order_id": 1,
            "status": "success"
        }

        # First call
        res1 = self.client.post("/payments/webhook/", payload)

        # Duplicate call
        res2 = self.client.post("/payments/webhook/", payload)

        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)

        # Should not double process
        from.models import Payment
        self.assertEqual(
            Payment.objects.filter(razorpay_payment_id="pay_456").count(),
            1
        )