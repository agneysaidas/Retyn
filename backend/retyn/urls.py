"""
URL configuration for retyn project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from rest_framework.authtoken.views import obtain_auth_token
from core.views import HealthCheck, ReadinessCheck

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/',obtain_auth_token),
    path('products/',include('products.urls')),
    path('cart/',include('carts.urls')),
    path('order/',include('orders.urls')),
    path('api/',include('orders.urls')),
    path("health/", HealthCheck.as_view()),
    path("ready/", ReadinessCheck.as_view()),
]
