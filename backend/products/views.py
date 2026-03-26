from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer

class ProductListView(APIView):
    def get(self,request):
        products = Product.objects.filter(is_active = True)
        serializer = ProductSerializer(products,many=True)
        return Response(serializer.data)
    
class ProductDetailView(APIView):
    def get(self,request,pk):
        product = Product.objects.get(id = pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)