from django.contrib import admin  # type: ignore
from .models import Company, Density, Product, Invoice, InvoiceItem, AuditLog, Receipt, InvoiceAudit  # type: ignore

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
    list_display = ('id', 'customer_name', 'customer_phone', 'date', 'total_amount', 'payment_method', 'payment_status')
    list_filter = ('payment_method', 'payment_status', 'date', 'is_deleted')
    search_fields = ('customer_name', 'customer_phone', 'id')
    inlines = [InvoiceItemInline]

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'user', 'timestamp')
    list_filter = ('entity_type', 'timestamp', 'user')

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'amount', 'date', 'is_cancelled')
    list_filter = ('is_cancelled', 'date')

@admin.register(InvoiceAudit)
class InvoiceAuditAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'action', 'timestamp')
