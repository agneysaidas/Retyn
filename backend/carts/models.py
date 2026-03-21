from django.db import models

class Cart(models.Model):
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='carts'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='carts'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(
        'Cart',
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
    )
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    sub_total = models.DecimalField(max_digits=10,decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name}*{self.quantity}"