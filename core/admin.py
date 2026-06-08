from django.contrib import admin  # type: ignore
from .models import Product, Invoice, InvoiceItem, AuditLog, Receipt, InvoiceAudit  # type: ignore

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'wholesale_price', 'bulk_wholesale_price', 'cost', 'stock_quantity', 'created_at')
    list_filter = ('is_available', 'created_at')
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
