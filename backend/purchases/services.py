from products.models import Batch,Inventory,InventoryLog

def receive_purchases(purchase):
    if purchase.status == 'received':
        raise Exception("Already received")
    
    for item in purchase.items.all():
        #Create Batch
        batch,created= Batch.objects.get_or_create(
            product = item.product,
            store = purchase.store,
            batch_number = item.batch_number,
            defaults={
                'expiry_date':item.expiry_date,
                'purchase_price':item.cost_price,
                'selling_price':item.cost_rice * 1.2,
                'quantity':0
            }
        )
        
        batch.quantity += item.quantity
        batch.save()
        
        #update Inventory
        inventory, created = Inventory.objects.get_or_create(
            product = item.product,
            store = purchase.store,
            defaults={'quantity':0}
        )
        
        inventory.quantity += item.quantity
        inventory.save()
        
        #log
        InventoryLog.objects.create(
            store = purchase.store,
            product=item.product,
            batch = batch,
            change= item.quantity,
            reason = 'purchase',
            reference_id = purchase.id
        )
        
    purchase.status = 'received'
    purchase.save()