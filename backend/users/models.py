from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    '''
    Defines how users are created
    Required when you override default user fields (like removing username).
    '''
    
    def create_user(self,email,password=None,**extra_fields):
        if not email:
            raise ValueError("Email is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email,**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self,email,password=None,**extra_fields):
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        
        if not password:
            raise ValueError("Superuser must have a password")
        
        return self.create_user(email,password,**extra_fields)

class User(AbstractUser):
    #custom user model inherits all Django auth features.
    username = None
    
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    
    ROLE_CHOICES = (
        ('admin','Admin'),
        ('manager','Manager'),
        ('cashier','Cashier'),
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES)
    
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    def __str__(self):
        #Controls how user is displayed (admin panel, shell, etc.).
        return self.email