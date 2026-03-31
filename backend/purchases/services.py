from decimal import Decimal

from products.models import Batch,Inventory,InventoryLog
import logging 
from django.db import transaction,models

logger = logging.getLogger(__name__)

def receive_purchases(purchase):
    logger.info(f"Receiving purchase {purchase.id}")
    if purchase.status == 'received':
        logger.warning(f"Duplicate receive attempt for purchase {purchase.id}")
        raise Exception("Already received")
    
    with transaction.atomic():
    
        for item in purchase.items.all():
            logger.info(f"Processing product {item.product.id} for purchase {purchase.id}")
            #Create Batch
            batch,created= Batch.objects.get_or_create(
                product = item.product,
                store = purchase.store,
                batch_number = item.batch_number,
                defaults={
                    'expiry_date':item.expiry_date,
                    'purchase_price':item.cost_price,
                    'selling_price':item.cost_rice * Decimal(1.2),
                    'quantity':0
                }
            )
            
            Batch.objects.filter(id=batch.id).update(
                quantity = models.F('quantity')+item.quantity
            )
            
            logger.info(f"Batch {batch.id} uppdated with + {item.quantity}")
            
            #update Inventory
            inventory, created = Inventory.objects.get_or_create(
                product = item.product,
                store = purchase.store,
                defaults={'quantity':0}
            )
            
            Inventory.objects.filter(id=inventory.id).update(quantity=models.F('quantity')+item.quantity)
            
            logger.info(f"Inventory uppdated for product {item.product.id}")
            
            #log
            InventoryLog.objects.create(
                store = purchase.store,
                product=item.product,
                batch = batch,
                change= item.quantity,
                reason = 'PURCHASE',
                reference_id = purchase.id
            )
            
        purchase.status = 'received'
        purchase.save()
        
        logger.info(f"Purchase {purchase.id} marked as received")