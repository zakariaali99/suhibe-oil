import os
import django  # type: ignore

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oilsystem.settings')
django.setup()

from django.contrib.auth.models import User # type: ignore
from core.models import Product, Invoice, InvoiceItem, Receipt, AuditLog, InvoiceAudit # type: ignore

def populate():
    print("Clearing all data...")
    InvoiceItem.objects.all().delete()
    Receipt.objects.all().delete()
    InvoiceAudit.objects.all().delete()
    Invoice.objects.all().delete()
    Product.objects.all().delete()
    AuditLog.objects.all().delete()
    User.objects.all().delete()

    print("Creating admin user...")
    User.objects.create_superuser('zakaria', 'zakaria@example.com', 'zak12345')
    print("User 'zakaria' created with password 'zak12345'")

    # Products with combined name/density and wholesale/bulk wholesale prices
    products = [
        # name, price, wholesale_price, bulk_wholesale_price, cost
        ('كاسترول Magnatec 5W-30', 150.00, 130.00, 110.00, 95.00),
        ('كاسترول Edge 10W-40', 180.00, 160.00, 140.00, 120.00),
        ('شل Helix Ultra 5W-30', 160.00, 140.00, 120.00, 105.00),
        ('شل Rimula 20W-50', 220.00, 195.00, 175.00, 150.00),
        ('موبيل Super 3000 5W-30', 145.00, 125.00, 110.00, 90.00),
        ('توتال Quartz 9000 0W-20', 175.00, 155.00, 135.00, 115.00),
    ]

    for name, price, wholesale, bulk, cost in products:
        p, created = Product.objects.update_or_create(
            name=name,
            defaults={
                'price': price,
                'wholesale_price': wholesale,
                'bulk_wholesale_price': bulk,
                'cost': cost,
                'stock_quantity': 50,
                'is_available': True
            }
        )
        print(f"{'Updated' if not created else 'Added'} product: {name}")

if __name__ == '__main__':
    populate()
