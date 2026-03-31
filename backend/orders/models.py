from django.db import models

class Order(models.Model):
    STATUS_CHOICES = (
        ('PENDING','Pending'),
        ('CONFIRMED','Confirmed'),
        ('CANCELLED','Cancelled')
    )
    
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE
    )
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE
    )
    cart = models.OneToOneField(
        'carts.Cart',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    total_amount = models.DecimalField(max_digits=10,decimal_places=2)
    total_discount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    final_amount = models.DecimalField(max_digits=10,decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Order #{self.id}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product= models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    batch = models.ForeignKey(
        'products.Batch',
        on_delete=models.SET_NULL,
        null = True
    )
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10,decimal_places=2)
    discount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    final_price = models.DecimalField(max_digits=10,decimal_places=2)
    subtotal = models.DecimalField(max_digits=10,decimal_places=2)
    final_subtotal = models.DecimalField(max_digits=10,decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} * {self.quantity}"
    
class Payment(models.Model):
    PAYMENT_CHOICES = (
        ('CASH','Cash'),
        ('CARD','Card'),
        ('WALLET','Wallet')
    )
    PAYMENT_STATUS = [
        ('PENDING','Pending'),
        ('SUCCESS','Success'),
        ('FAILED','Failed'),
    ]
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES)
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    status= models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['razorpay_order_id']),
        ]