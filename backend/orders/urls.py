from django.urls import path
from .views import *
from .webhooks import payment_webhook
urlpatterns = [
    path('',OrderListView.as_view()),
    path('<int:order_id>/',OrderDetailView.as_view()),
    path('<int:order_id>/cancel/',CancelOrderView.as_view()),
    path('<int:order_id>/pay/',PaymentView.as_view()),
    path('<int:order_id>/create-payment-order/',CreatePaymentView.as_view()),
    path('payment/webhook/',payment_webhook)
]
