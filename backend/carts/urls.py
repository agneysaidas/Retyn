from django.urls import path
from .views import CartView, AddtoCartView,UpdateCartItemView,RemoveCartItemView,CheckoutView
urlpatterns = [
    path('',CartView.as_view()),
    path('add/',AddtoCartView.as_view()),
    path('update/',UpdateCartItemView.as_view()),
    path('remove/',RemoveCartItemView.as_view()),
    path('checkout/',CheckoutView.as_view())
]
