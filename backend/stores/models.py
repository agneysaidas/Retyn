from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20,unique=True,null=True,blank=True)
    address = models.TextField(null=True,blank=True)
    city = models.CharField(max_length=100,null=True,blank=True)
    state = models.CharField(max_length=100,null=True,blank=True)
    pincode = models.CharField(max_length=10,null=True,blank=True)
    phone = models.CharField(max_length=15,null=True,blank=True)
    is_active = models.BooleanField(default=True,null=True,blank=True)
    opened_date = models.DateField(unique=True,blank=True,null=True)
    closed_date = models.DateField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    
    def __str__(self):
        return self.name

