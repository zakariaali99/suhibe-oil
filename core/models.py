from django.db import models
from django.utils.translation import gettext_lazy as _

class Company(models.Model):
    name = models.CharField(_("Company Name"), max_length=255)
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
    name = models.CharField(_("Product Name"), max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="products", verbose_name=_("Company"))
    density = models.ForeignKey(Density, on_delete=models.CASCADE, related_name="products", verbose_name=_("Density"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name} - {self.density.value})"

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

class Invoice(models.Model):
    PAYMENT_METHODS = (
        ('cash', _('Cash')),
        ('card', _('Card')),
        ('transfer', _('Transfer')),
    )
    customer_name = models.CharField(_("Customer Name"), max_length=255)
    date = models.DateTimeField(_("Date"), auto_now_add=True)
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHODS)
    is_paid = models.BooleanField(_("Is Paid"), default=False)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=10, decimal_places=2, default=0)

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
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted Product'} x {self.quantity}"
