from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connections
from django.core.cache import cache


class HealthCheck(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class ReadinessCheck(APIView):
    def get(self, request):

        try:
            connections['default'].cursor()
            db_status = "ok"
        except Exception:
            db_status = "down"

        try:
            cache.set("health_check", "ok", timeout=5)
            redis_status = cache.get("health_check")
        except Exception:
            redis_status = "down"

        return Response({
            "database": db_status,
            "redis": redis_status
        })