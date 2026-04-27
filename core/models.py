from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from decimal import Decimal

class Company(models.Model):
    name = models.CharField(_("Company Name"), max_length=255) # Keep name field as per instruction, the snippet was contradictory
    payment_method = models.CharField(max_length=20, choices=[('cash', 'Cash'), ('card', 'Card'), ('transfer', 'Transfer')], default='cash')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")

class Density(models.Model):
    value = models.CharField(_("Density Value"), max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.value

    class Meta:
        verbose_name = _("Density")
        verbose_name_plural = _("Densities")

class Product(models.Model):
    name = models.CharField(_("Product Name"), max_length=255, db_index=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="products", verbose_name=_("Company"))
    density = models.ForeignKey(Density, on_delete=models.CASCADE, related_name="products", verbose_name=_("Density"))
    image = models.ImageField(_("Product Image"), upload_to='products/', null=True, blank=True) # Added image field
    price = models.DecimalField(_("Selling Price"), max_digits=10, decimal_places=2, default=0.00)
    cost = models.DecimalField(_("Cost Price"), max_digits=10, decimal_places=2, default=0.00)
    stock_quantity = models.PositiveIntegerField(_("Stock Quantity"), default=0)
    is_available = models.BooleanField(_("Is Available"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name}) - {self.price} LYD [Stock: {self.stock_quantity}]"

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            from PIL import Image
            img = Image.open(self.image.path)
            if img.height > 600 or img.width > 600:
                output_size = (600, 600)
                img.thumbnail(output_size)
                img.save(self.image.path)

class AuditLog(models.Model):
    action = models.CharField(_("Action"), max_length=255)
    entity_type = models.CharField(_("Entity Type"), max_length=50) # e.g. 'Company', 'Product'
    entity_id = models.IntegerField(_("Entity ID"), null=True, blank=True)
    details = models.TextField(_("Details"), null=True, blank=True)
    user = models.CharField(_("User"), max_length=150, null=True, blank=True)
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.entity_type} at {self.timestamp}"

class Invoice(models.Model):
    PAYMENT_METHODS = (
        ('cash', _('Cash')),
        ('card', _('Card')),
        ('transfer', _('Transfer')),
    )
    PAYMENT_STATUSES = (
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('unpaid', _('Unpaid')),
    )
    customer_name = models.CharField(_("Customer Name"), max_length=255)
    customer_phone = models.CharField(_("Customer Phone"), max_length=20, blank=True, default='', db_index=True)
    date = models.DateTimeField(_("Date"), auto_now_add=True)
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(_("Payment Status"), max_length=10, choices=PAYMENT_STATUSES, default='pending')
    total_amount = models.DecimalField(_("Total Amount"), max_digits=10, decimal_places=2, default=0)
    total_profit = models.DecimalField(_("Total Profit"), max_digits=10, decimal_places=2, default=0)
    
    is_draft = models.BooleanField(_("Is Draft"), default=False)
    is_deleted = models.BooleanField(_("Is Deleted"), default=False)
    deleted_at = models.DateTimeField(_("Deleted At"), null=True, blank=True)
    deleted_by = models.CharField(_("Deleted By"), max_length=150, null=True, blank=True)

    @property
    def total_paid(self):
        receipts = self.receipts.filter(is_cancelled=False).aggregate(total=models.Sum('amount'))
        return receipts['total'] or Decimal('0.00')

    @property
    def remaining_balance(self):
        return self.total_amount - self.total_paid

    @property
    def payment_progress(self):
        if self.total_amount <= 0:
            return 100 if self.payment_status == 'paid' else 0
        progress = (self.total_paid / self.total_amount) * 100
        return min(float(progress), 100.0)

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer_name}"

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Added cost_price
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Added profit
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        self.profit = (self.unit_price - self.cost_price) * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted Product'} x {self.quantity}"

class InvoiceAudit(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} on Invoice #{self.invoice.id}"

class Receipt(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="receipts")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Receipt for Invoice #{self.invoice.id} - {self.amount}"

    class Meta:
        verbose_name = _("Receipt")
        verbose_name_plural = _("Receipts")

class InternalPurchase(models.Model):
    EXPENSE_TYPES = (
        ('company', _('Company Expense')),
        ('personal', _('Personal Expense')),
    )
    PAYMENT_STATUSES = (
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('unpaid', _('Unpaid')),
    )
    supplier_name = models.CharField(_("Supplier"), max_length=255, blank=True)
    expense_type = models.CharField(_("Expense Type"), max_length=20, choices=EXPENSE_TYPES, default='company', db_index=True)
    date = models.DateTimeField(_("Date"), auto_now_add=True, db_index=True)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(_("Total Paid"), max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(_("Payment Status"), max_length=10, choices=PAYMENT_STATUSES, default='unpaid')
    notes = models.TextField(_("Notes"), blank=True)
    created_by = models.CharField(_("Created By"), max_length=150, blank=True)

    @property
    def remaining_balance(self):
        return self.total_amount - self.total_paid

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier_name} ({self.get_expense_type_display()})"

    class Meta:
        verbose_name = _("Internal Purchase")
        verbose_name_plural = _("Internal Purchases")

class InternalPurchaseItem(models.Model):
    purchase = models.ForeignKey(InternalPurchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    unit_cost = models.DecimalField(_("Unit Cost"), max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted Product'} x {self.quantity}"
