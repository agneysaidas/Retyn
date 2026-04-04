from django.db import models
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
class Product(models.Model):
    name = models.CharField(max_length= 255)
    brand = models.CharField(max_length=255)
    category = models.ForeignKey(
        'products.Category',
        on_delete=models.CASCADE,
        related_name='products'
    )
    barcode = models.CharField(max_length=100,unique=True)
    description = models.TextField(null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
class Inventory(models.Model):
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    
    quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('store','product')
        
    def __str__(self):
        return f"{self.product.name} - {self.store.name}"
    
class Price(models.Model):
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='prices'
    )
    
    base_price = models.DecimalField(max_digits=10,decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5,decimal_places=2)
    is_vat_inclusive = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now=True)
    end_date = models.DateTimeField(null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.base_price}"
    
    def get_final_price(self):
        if self.is_vat_inclusive:
            return self.base_price
        return self.base_price + (self.base_price*self.vat_rate/Decimal('100'))
    
    class Meta:
        ordering = ['-start_date']
        
class Batch(models.Model):
    product = models.ForeignKey(
        'products.Product',
        on_delete= models.CASCADE,
        related_name='batches'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='batches'
    )
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    quantity = models.IntegerField()
    reserved_quantity = models.IntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10,decimal_places=2)
    selling_price = models.DecimalField(max_digits=10,decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product','store','batch_number')
        
        indexes = [
            models.Index(fields=['product','store','expiry_date'])
        ]
        
    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"
    
class InventoryLog(models.Model):
    CHANGE_TYPE=(
        ('sale',"Sale"),
        ('purchase','Purchase'),
        ('adjustment','Adjustment'),
        ('return','Reutrn')
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    batch = models.ForeignKey(
        'products.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    change=models.IntegerField()
    reason = models.CharField(max_length=20,choices=CHANGE_TYPE)
    reference_id = models.IntegerField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} ({self.change})"