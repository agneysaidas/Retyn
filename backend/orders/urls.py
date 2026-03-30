from django.urls import path
from .views import *

urlpatterns = [
    path('<int:order_id>/cancel/',CancelOrderView.as_view()),
]
