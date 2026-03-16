import os
import django  # type: ignore

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oilsystem.settings')
django.setup()

from django.contrib.auth.models import User # type: ignore
from core.models import Company, Density, Product, Invoice, InvoiceItem, Receipt, AuditLog, InvoiceAudit # type: ignore

def populate():
    print("Clearing all data...")
    InvoiceItem.objects.all().delete()
    Receipt.objects.all().delete()
    InvoiceAudit.objects.all().delete()
    Invoice.objects.all().delete()
    Product.objects.all().delete()
    Density.objects.all().delete()
    Company.objects.all().delete()
    AuditLog.objects.all().delete()
    User.objects.all().delete()

    print("Creating admin user...")
    User.objects.create_superuser('zakaria', 'zakaria@example.com', 'zak12345')
    print("User 'zakaria' created with password 'zak12345'")

    # Companies
    companies = ['كاسترول (Castrol)', 'شل (Shell)', 'موبيل (Mobil)', 'توتال (Total)']
    company_objs = []
    for c_name in companies:
        c, created = Company.objects.get_or_create(name=c_name)
        company_objs.append(c)
        print(f"Added company: {c_name}")

    # Densities
    densities = ['5W-30', '10W-40', '20W-50', '0W-20']
    density_objs = []
    for d_val in densities:
        d, created = Density.objects.get_or_create(value=d_val)
        density_objs.append(d)
        print(f"Added density: {d_val}")

    # Products
    products = [
        ('Magnatec', company_objs[0], density_objs[0], 150.00, 110.00),
        ('Edge', company_objs[0], density_objs[1], 180.00, 130.00),
        ('Helix Ultra', company_objs[1], density_objs[0], 160.00, 120.00),
        ('Rimula', company_objs[1], density_objs[2], 220.00, 170.00),
        ('Super 3000', company_objs[2], density_objs[0], 145.00, 105.00),
        ('Quartz 9000', company_objs[3], density_objs[3], 175.00, 125.00),
    ]

    for p_name, comp, dens, sell, cost in products:
        p, created = Product.objects.get_or_create(
            name=p_name, 
            company=comp, 
            density=dens, 
            defaults={'price': sell, 'cost': cost}
        )
        print(f"Added product: {p_name} - {comp.name}")

if __name__ == '__main__':
    populate()
