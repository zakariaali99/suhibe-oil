from django.contrib import admin  # type: ignore
from .models import Company, Density, Product, Invoice, InvoiceItem  # type: ignore

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Density)
class DensityAdmin(admin.ModelAdmin):
    list_display = ('value', 'created_at')
    search_fields = ('value',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'density', 'created_at')
    list_filter = ('company', 'density')
    search_fields = ('name',)

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'date', 'total_amount', 'payment_method', 'is_paid')
    list_filter = ('payment_method', 'is_paid', 'date')
    search_fields = ('customer_name', 'id')
    inlines = [InvoiceItemInline]
