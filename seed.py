import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oilsystem.settings')
django.setup()

from core.models import Company, Density, Product

def populate():
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
        ('Magnatec', company_objs[0], density_objs[0]),
        ('Edge', company_objs[0], density_objs[1]),
        ('Helix Ultra', company_objs[1], density_objs[0]),
        ('Rimula', company_objs[1], density_objs[2]),
        ('Super 3000', company_objs[2], density_objs[0]),
        ('Quartz 9000', company_objs[3], density_objs[3]),
    ]

    for p_name, comp, dens in products:
        p, created = Product.objects.get_or_create(name=p_name, company=comp, density=dens)
        print(f"Added product: {p_name} - {comp.name}")

if __name__ == '__main__':
    populate()
