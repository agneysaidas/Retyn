from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255,null=True,blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(null=True,blank=True)
    address= models.TextField()
    
    def __str__(self):
        return self.name
