import os
import django  # type: ignore

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oilsystem.settings')
django.setup()

from core.models import Product, Invoice, InvoiceItem, InvoiceAudit, Receipt, AuditLog, InternalPurchase, InternalPurchaseItem  # type: ignore
from django.contrib.auth.models import User

def reset():
    print("Deleting transactional data...")
    InternalPurchaseItem.objects.all().delete()
    InternalPurchase.objects.all().delete()
    InvoiceItem.objects.all().delete()
    InvoiceAudit.objects.all().delete()
    Receipt.objects.all().delete()
    Invoice.objects.all().delete()
    AuditLog.objects.all().delete()
    
    print("Deleting master data...")
    Product.objects.all().delete()

    print("Restoring administrator if missing...")
    if not User.objects.filter(username='suhaib').exists():
        User.objects.create_superuser('suhaib', 'suhaib@example.com', 'oil')
        print("Superuser created.")
    else:
        print("Superuser suhaib preserved.")

    print("DB reset complete. Ready for seeding.")

if __name__ == '__main__':
    reset()
