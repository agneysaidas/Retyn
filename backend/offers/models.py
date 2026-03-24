from django.db import models

class Offer(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage','Percentage'),
        ('fixed','Fixed Amount'),
    )
    name = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=20,choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10,decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)
    min_cart_value = models.DecimalField(max_digits=10,decimal_places=2)
    max_discount_value = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    priority = models.IntegerField(default=0)
    usage_limit = models.IntegerField(null=True,blank=True)
    used_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
class OfferProduct(models.Model):
    offer = models.ForeignKey(
        'Offer',
        on_delete = models.CASCADE
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )

class OfferCategory(models.Model):
    offer = models.ForeignKey(
        'Offer',
        on_delete = models.CASCADE
    )
    category = models.ForeignKey(
        'products.Category',
        on_delete=models.CASCADE
    )
    
class OfferStore(models.Model):
    offer = models.ForeignKey(
        'Offer',
        on_delete = models.CASCADE
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE
    )

class OfferDay(models.Model):
    DAY_CHOICES=(
        (0,'Monday'),
        (1,'Tuesday'),
        (2,'Wednesday'),
        (3,'Thursday'),
        (4,'Friday'),
        (5,'Saturday'),
        (6,'Sunday'),
    )
    offer = models.ForeignKey(
        'Offer',
        on_delete=models.CASCADE
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
