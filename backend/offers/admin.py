from django.contrib import admin
from .models import *

admin.site.register(Offer)
admin.site.register(OfferCategory)
admin.site.register(OfferDay)
admin.site.register(OfferProduct)
admin.site.register(OfferStore)
admin.site.register(OfferUsage)