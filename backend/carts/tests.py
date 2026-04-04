from django.test import TestCase
from django.contrib.auth import get_user_model
from carts.models import Cart, CartItem
from products.models import Product, Batch
from carts.services import checkout
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class CheckoutTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email="test@test.com",
            password="pass"
        )

        # ⚠️ FIX THIS BASED ON YOUR MODEL
        self.store = getattr(self.user, "store", None)

        # Create product
        self.product = Product.objects.create(
            name="Test Product",
            category_id=1
        )

        # Create valid batch
        self.batch = Batch.objects.create(
            product=self.product,
            store=self.store,
            quantity=10,
            reserved_quantity=0,
            selling_price=Decimal("100"),
            expiry_date=timezone.now() + timedelta(days=10)
        )

        # Create cart
        self.cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            is_active=True
        )

        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )

    # ✅ 1. HAPPY PATH
    def test_checkout_success(self):
        order = checkout(self.cart, "key-1")

        self.assertEqual(order.final_amount, Decimal("200"))
        self.assertEqual(order.items.count(), 1)

    # ✅ 2. IDEMPOTENCY (CRITICAL)
    def test_idempotency_same_key(self):
        order1 = checkout(self.cart, "same-key")
        order2 = checkout(self.cart, "same-key")

        self.assertEqual(order1.id, order2.id)

    # ✅ 3. DIFFERENT KEYS CREATE DIFFERENT ORDERS
    def test_different_keys_create_new_orders(self):
        order1 = checkout(self.cart, "key-1")

        # Need new cart because old one is inactive
        new_cart = Cart.objects.create(
            user=self.user,
            store=self.store,
            is_active=True
        )

        CartItem.objects.create(
            cart=new_cart,
            product=self.product,
            quantity=2
        )

        order2 = checkout(new_cart, "key-2")

        self.assertNotEqual(order1.id, order2.id)

    # ✅ 4. INSUFFICIENT STOCK
    def test_insufficient_stock(self):
        # Request more than available
        item = self.cart.items.first()
        item.quantity = 100
        item.save()

        with self.assertRaises(Exception):
            checkout(self.cart, "key-stock-fail")

    # ✅ 5. CART GETS DEACTIVATED
    def test_cart_deactivated_after_checkout(self):
        checkout(self.cart, "key-3")

        self.cart.refresh_from_db()
        self.assertFalse(self.cart.is_active)

    # ✅ 6. RESERVED QUANTITY UPDATED
    def test_reserved_quantity_updated(self):
        checkout(self.cart, "key-4")

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.reserved_quantity, 2)

    # ✅ 7. EXPIRED BATCH SHOULD NOT BE USED
    def test_expired_batch_ignored(self):
        self.batch.expiry_date = timezone.now() - timedelta(days=1)
        self.batch.save()

        with self.assertRaises(Exception):
            checkout(self.cart, "key-expired")

    # ✅ 8. PARTIAL BATCH ALLOCATION (ADVANCED CASE)
    def test_multiple_batches_used(self):
        # reduce first batch
        self.batch.quantity = 1
        self.batch.save()

        # create second batch
        Batch.objects.create(
            product=self.product,
            store=self.store,
            quantity=5,
            reserved_quantity=0,
            selling_price=Decimal("100"),
            expiry_date=timezone.now() + timedelta(days=10)
        )

        order = checkout(self.cart, "key-multi")

        self.assertEqual(order.items.count(), 2)  # split across batches

    # ✅ 9. ORDER TOTAL CONSISTENCY
    def test_order_total_consistency(self):
        order = checkout(self.cart, "key-total")

        calculated_total = sum(
            item.final_subtotal for item in order.items.all()
        )

        self.assertEqual(order.final_amount, calculated_total)