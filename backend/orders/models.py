from django.db import models

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending','Pending'),
        ('completed','Completed'),
        ('canccelled','Cancelled')
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
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
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
    final_price = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    subtotal = models.DecimalField(max_digits=10,decimal_places=2)
    final_subtotal = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    
    def __str__(self):
        return f"{self.product.name} * {self.quantity}"
    
class Payment(models.Model):
    PAYMENT_CHOICES = (
        ('cash','Cash'),
        ('card','Card'),
        ('wallet','Wallet')
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    method = models.CharField(max_length=20,choices=PAYMENT_CHOICES)
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    status= models.CharField(max_length=20,default='completed')
    created_at = models.DateTimeField(auto_now_add=True)