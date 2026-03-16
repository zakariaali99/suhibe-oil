from django.db import migrations, models

def migrate_is_paid(apps, schema_editor):
    Invoice = apps.get_model('core', 'Invoice')
    for invoice in Invoice.objects.all():
        if getattr(invoice, 'is_paid', False):
            invoice.payment_status = 'paid'
        else:
            invoice.payment_status = 'unpaid'
        invoice.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_remove_company_total_profit_product_is_available"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("action", models.CharField(max_length=255, verbose_name="Action")),
                (
                    "entity_type",
                    models.CharField(max_length=50, verbose_name="Entity Type"),
                ),
                (
                    "entity_id",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="Entity ID"
                    ),
                ),
                (
                    "details",
                    models.TextField(blank=True, null=True, verbose_name="Details"),
                ),
                (
                    "user",
                    models.CharField(
                        blank=True, max_length=150, null=True, verbose_name="User"
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(auto_now_add=True, verbose_name="Timestamp"),
                ),
            ],
        ),
        migrations.AddField(
            model_name="invoice",
            name="customer_phone",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=20,
                verbose_name="Customer Phone",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Deleted At"
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="deleted_by",
            field=models.CharField(
                blank=True, max_length=150, null=True, verbose_name="Deleted By"
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("paid", "Paid"),
                    ("unpaid", "Unpaid"),
                ],
                default="pending",
                max_length=10,
                verbose_name="Payment Status",
            ),
        ),
        migrations.RunPython(migrate_is_paid),
        migrations.RemoveField(
            model_name="invoice",
            name="is_paid",
        ),
    ]

def migrate_is_paid(apps, schema_editor):
    Invoice = apps.get_model('core', 'Invoice')
    for invoice in Invoice.objects.all():
        if invoice.is_paid:
            invoice.payment_status = 'paid'
        else:
            invoice.payment_status = 'unpaid'
        invoice.save()
