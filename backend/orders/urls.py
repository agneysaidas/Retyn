from django.urls import path
from .views import *

urlpatterns = [
    path('',OrderListView.as_view()),
    path('<int:order_id>/',OrderDetailView.as_view()),
    path('<int:order_id>/cancel/',CancelOrderView.as_view()),
    path('<int:order_id>/pay/',PaymentView.as_view()),
]
