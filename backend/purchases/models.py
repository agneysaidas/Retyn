from django.db import models

class Purchase(models.Model):
    STATUS_CHOICES = (
        ('pending','Pending'),
        ('received','Received')
    )
    
    supplier= models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.CASCADE
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    total_amount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Purchase #{self.id}"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    quantity = models.IntegerField()
    cost_price = models.DecimalField(max_digits=10,decimal_places=2)
    selling_price=  models.DecimalField(max_digits=10,decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} ({self.quantity})"