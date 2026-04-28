from django.shortcuts import render, redirect, get_object_or_404  # type: ignore
from django.contrib import messages  # type: ignore
from django.db.models import Q, Count, Sum, F  # type: ignore
from django.http import HttpResponse  # type: ignore
from django.template.loader import render_to_string  # type: ignore
from django.views.decorators.http import require_POST  # type: ignore
from django.contrib.auth import login, authenticate, logout # type: ignore
from django.contrib.auth.decorators import login_required # type: ignore
from django.contrib.auth.forms import AuthenticationForm # type: ignore
from .models import Company, Density, Product, Invoice, InvoiceItem, InvoiceAudit, Receipt, AuditLog, InternalPurchase, InternalPurchaseItem
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# PDF generation imports
from xhtml2pdf import pisa  # type: ignore
import io
import os
import csv
from django.conf import settings  # type: ignore
from django.contrib.staticfiles import finders  # type: ignore
from django.utils import timezone
from datetime import timedelta, datetime
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "عذراً، لا تملك الصلاحيات الكافية للوصول لهذه الصفحة.")
            return redirect('product_list')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources on the disk.
    """
    # Try finding via Django finders first (best for development)
    result = finders.find(uri)
    if result:
        if isinstance(result, (list, tuple)):
            path = result[0]
        else:
            path = result
        return path

    # Fallback to manual path construction if finders fail
    static_url = settings.STATIC_URL
    static_root = settings.STATIC_ROOT
    media_url = settings.MEDIA_URL
    media_root = settings.MEDIA_ROOT

    if uri.startswith(static_url):
        path = os.path.join(static_root, uri.replace(static_url, ""))
    elif uri.startswith(media_url):
        path = os.path.join(media_root, uri.replace(media_url, ""))
    else:
        # If it's a relative path, try joining with static root as a last resort
        path = os.path.join(static_root, uri)

    # Final check
    if os.path.isfile(path):
        return path
    
    return uri

# --- POS Views ---

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    company_id = request.GET.get('company')
    density_id = request.GET.get('density')
    
    products = Product.objects.filter(is_available=True).select_related('company', 'density')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(company__name__icontains=query) | 
            Q(density__value__icontains=query)
        )
    
    if company_id:
        products = products.filter(company_id=company_id)
    if density_id:
        products = products.filter(density_id=density_id)
    
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total_qty = 0
    if cart:
        cart_products = {p.id: p for p in Product.objects.filter(id__in=cart.keys())}
        for pid, qty in cart.items():
            prod = cart_products.get(int(pid))
            if prod:
                cart_items.append({'product': prod, 'quantity': qty})
                cart_total_qty += qty

    companies = Company.objects.annotate(product_count=Count('products')).filter(product_count__gt=0)
    densities = Density.objects.annotate(product_count=Count('products')).filter(product_count__gt=0)

    return render(request, 'main/product_list.html', {
        'products': products,
        'cart_items': cart_items,
        'cart_total_qty': cart_total_qty,
        'query': query,
        'selected_company': company_id,
        'selected_density': density_id,
        'companies': companies,
        'densities': densities,
    })

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if not product.is_available:
        messages.error(request, "هذا المنتج غير متوفر حالياً.")
        return redirect('product_list')
        
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    cart[product_id_str] = cart.get(product_id_str, 0) + 1
    request.session['cart'] = cart
    messages.success(request, "تمت إضافة المنتج للعربة.")
    return redirect('product_list')

@login_required
@require_POST
def update_cart_qty(request, product_id, action):
    cart = request.session.get('cart', {})
    pid_str = str(product_id)
    if pid_str in cart:
        if action == 'plus':
            cart[pid_str] += 1
        elif action == 'minus':
            cart[pid_str] -= 1
            if cart[pid_str] <= 0:
                del cart[pid_str]
    request.session['cart'] = cart
    return redirect('product_list')

@login_required
@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        messages.info(request, "تمت إزالة المنتج من العربة.")
    return redirect('product_list')

@login_required
@require_POST
def clear_cart(request):
    request.session['cart'] = {}
    return redirect('product_list')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "العربة فارغة!")
        return redirect('product_list')
    
    products_in_cart = []
    cart_to_cleanup = []
    
    for pid, qty in cart.items():
        prod = Product.objects.filter(id=pid).first()
        if prod:
            products_in_cart.append({'product': prod, 'quantity': qty})
        else:
            cart_to_cleanup.append(pid)
            
    if cart_to_cleanup:
        for pid in cart_to_cleanup:
            del cart[pid]
        request.session['cart'] = cart
        messages.warning(request, "تمت إزالة بعض المنتجات من العربة لأنها لم تعد متوفرة في النظام.")

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        payment_method = request.POST.get('payment_method')
        
        if not customer_name:
            messages.error(request, "يرجى إدخال اسم العميل.")
            return render(request, 'main/checkout.html', {'products_in_cart': products_in_cart})

        import re
        if customer_phone and not re.match(r'^09[0-9]{8}$', customer_phone):
            messages.error(request, "رقم الهاتف غير صحيح. يجب أن يبدأ بـ 09 ويتكون من 10 أرقام.")
            return render(request, 'main/checkout.html', {
                'products_in_cart': products_in_cart,
                'customer_name': customer_name,
                'customer_phone': customer_phone
            })

        try:
            initial_status = request.POST.get('initial_status', 'pending')
            # Create Invoice
            invoice = Invoice.objects.create(
                customer_name=customer_name,
                customer_phone=customer_phone,
                payment_method=payment_method,
                payment_status=initial_status
            )
            
            subtotals = []
            profits = []

            for item in products_in_cart:
                prod = item['product']
                pid = str(prod.id)
                qty_str = request.POST.get(f'qty_{pid}', str(item['quantity'])).strip()
                qty = int(qty_str) if qty_str else 0
                
                if qty <= 0: continue

                # Auto-pull prices from product
                price = prod.price
                cost = prod.cost

                qty_decimal = Decimal(qty)
                subtotal = price * qty_decimal
                profit = (price - cost) * qty_decimal

                ii = InvoiceItem.objects.create(
                    invoice=invoice,
                    product=prod,
                    quantity=qty,
                    unit_price=price,
                    cost_price=cost
                )
                
                # Update Stock
                prod.stock_quantity = F('stock_quantity') - qty
                prod.save()
                
                subtotals.append(subtotal)
                profits.append(profit)
            
            invoice.total_amount = sum(subtotals) if subtotals else Decimal('0.00')
            invoice.total_profit = sum(profits) if profits else Decimal('0.00')
            
            if initial_status == 'paid' and invoice.total_amount > 0:
                payment_type_name = 'نقداً' if payment_method == 'cash' else 'بطاقة' if payment_method == 'card' else 'تحويل'
                Receipt.objects.create(
                    invoice=invoice,
                    amount=invoice.total_amount,
                    notes=f"دفع كامل عند الإصدار ({payment_type_name})"
                )
                
            invoice.save()

            InvoiceAudit.objects.create(
                invoice=invoice,
                action="تم إنشاء الفاتورة",
                details=f"بواسطة العميل: {invoice.customer_name} ({invoice.customer_phone})"
            )
            
            request.session['cart'] = {}
            return redirect('invoice_view', invoice_id=invoice.id)
            
        except (InvalidOperation, ValueError):
            messages.error(request, "خطأ في القيم المدخلة.")
            return render(request, 'main/checkout.html', {'products_in_cart': products_in_cart})

    return render(request, 'main/checkout.html', {
        'products_in_cart': products_in_cart
    })

@login_required
def invoice_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'main/invoice.html', {'invoice': invoice})

@login_required
def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    html_string = render_to_string('pdf/invoice_pdf.html', {'invoice': invoice, 'STATIC_URL': settings.STATIC_URL})
    
    result = io.BytesIO()
    pdf = pisa.pisaDocument(
        io.BytesIO(html_string.encode("UTF-8")), 
        result,
        encoding='UTF-8',
        link_callback=link_callback
    )
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"invoice_{invoice.id}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

# --- Dashboard Views ---

@login_required
@admin_required
def dashboard(request):
    # KPIs
    total_revenue = Receipt.objects.filter(is_cancelled=False).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_net_profit = Invoice.objects.filter(is_deleted=False).aggregate(total=Sum('total_profit'))['total'] or Decimal('0.00')
    
    # Stock Value (Current Cost * Stock Qty)
    stock_value = Product.objects.all().aggregate(
        total=Sum(F('cost') * F('stock_quantity'))
    )['total'] or Decimal('0.00')
    
    # Debts (Optimized aggregation)
    unpaid_invoices_agg = Invoice.objects.filter(is_deleted=False).exclude(payment_status='paid')
    total_due = unpaid_invoices_agg.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_received = Receipt.objects.filter(invoice__in=unpaid_invoices_agg, is_cancelled=False).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    customer_debt = total_due - total_received
    
    unpaid_purchases_agg = InternalPurchase.objects.exclude(payment_status='paid')
    total_purch_due = unpaid_purchases_agg.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_purch_paid = unpaid_purchases_agg.aggregate(total=Sum('total_paid'))['total'] or Decimal('0.00')
    company_debt = total_purch_due - total_purch_paid

    stats = {
        'companies': Company.objects.count(),
        'densities': Density.objects.count(),
        'products': Product.objects.count(),
        'invoices': Invoice.objects.filter(is_deleted=False).count(),
        'total_revenue': total_revenue,
        'total_net_profit': total_net_profit,
        'stock_value': stock_value,
        'customer_debt': customer_debt,
        'company_debt': company_debt,
    }
    
    return render(request, 'dashboard/index.html', {'stats': stats})

# Companies
@login_required
def manage_companies(request):
    companies = Company.objects.all().order_by('-created_at')
    return render(request, 'dashboard/companies.html', {'companies': companies})

@require_POST
@login_required
def add_company(request):
    name = request.POST.get('name', '').strip()
    if name:
        Company.objects.create(name=name)
        messages.success(request, "تمت إضافة الشركة.")
    else:
        messages.error(request, "اسم الشركة مطلوب.")
    return redirect('manage_companies')

@require_POST
@login_required
def edit_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    name = request.POST.get('name', '').strip()
    if name:
        company.name = name
        company.save()
        messages.success(request, "تم تحديث الشركة.")
    return redirect('manage_companies')

@require_POST
@login_required
def delete_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    
    # Capture product names for audit
    product_names = list(company.products.values_list('name', flat=True))
    details = f"حذف الشركة: {company.name}. المنتجات المتأثرة: {', '.join(product_names)}"
    
    AuditLog.objects.create(
        action="حذف شركة",
        entity_type="Company",
        entity_id=company.id,
        details=details,
        user=request.user.username
    )
    
    company.delete()
    messages.info(request, "تم حذف الشركة بنجاح.")
    return redirect('manage_companies')

# Densities
@login_required
def manage_densities(request):
    densities = Density.objects.all().order_by('-created_at')
    return render(request, 'dashboard/densities.html', {'densities': densities})

@login_required
@require_POST
def add_density(request):
    value = request.POST.get('value', '').strip()
    if value:
        Density.objects.create(value=value)
        messages.success(request, "تمت إضافة الكثافة.")
    else:
        messages.error(request, "قيمة الكثافة مطلوبة.")
    return redirect('manage_densities')

@require_POST
@login_required
def edit_density(request, pk):
    density = get_object_or_404(Density, pk=pk)
    value = request.POST.get('value', '').strip()
    if value:
        density.value = value
        density.save()
        messages.success(request, "تم تحديث الكثافة.")
    return redirect('manage_densities')

@require_POST
@login_required
def delete_density(request, pk):
    density = get_object_or_404(Density, pk=pk)
    density.delete()
    messages.info(request, "تم حذف الكثافة.")
    return redirect('manage_densities')

# Products
@login_required
def manage_products(request):
    products = Product.objects.all().select_related('company', 'density').order_by('-created_at')
    companies = Company.objects.all()
    densities = Density.objects.all()
    return render(request, 'dashboard/products.html', {
        'products': products,
        'companies': companies,
        'densities': densities
    })

@login_required
@require_POST
def add_product(request):
    name = request.POST.get('name', '').strip()
    company_id = request.POST.get('company_id')
    density_id = request.POST.get('density_id')
    image = request.FILES.get('image')
    is_available = request.POST.get('is_available') == 'on'
    price = request.POST.get('price', '0')
    cost = request.POST.get('cost', '0')
    stock_quantity = request.POST.get('stock_quantity', '0')
    
    if name and company_id and density_id:
        company = get_object_or_404(Company, id=company_id)
        density = get_object_or_404(Density, id=density_id)
        
        Product.objects.create(
            name=name,
            company=company,
            density=density,
            image=image,
            is_available=is_available,
            price=Decimal(price or '0'),
            cost=Decimal(cost or '0'),
            stock_quantity=int(stock_quantity or 0),
        )
        messages.success(request, "تمت إضافة المنتج.")
    else:
        messages.error(request, "جميع الحقول مطلوبة.")
    return redirect('manage_products')

@require_POST
@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = request.POST.get('name', '').strip()
    company_id = request.POST.get('company_id')
    density_id = request.POST.get('density_id')
    image = request.FILES.get('image')
    price = request.POST.get('price', '0')
    cost = request.POST.get('cost', '0')
    stock_quantity = request.POST.get('stock_quantity')
    
    if name and company_id and density_id:
        product.name = name
        product.company_id = company_id
        product.density_id = density_id
        product.is_available = request.POST.get('is_available') == 'on'
        product.price = Decimal(price or '0')
        product.cost = Decimal(cost or '0')
        if stock_quantity is not None:
            product.stock_quantity = int(stock_quantity or 0)
        if image:
            product.image = image
        product.save()
        messages.success(request, "تم تحديث المنتج.")
    return redirect('manage_products')

@require_POST
@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.info(request, "تم حذف المنتج.")
    return redirect('manage_products')

# Invoices
@login_required
@admin_required
def invoice_list(request):
    query = request.GET.get('q')
    paid_filter = request.GET.get('paid')
    method_filter = request.GET.get('method')
    date_preset = request.GET.get('date_preset')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    invoices = Invoice.objects.filter(is_deleted=False).select_related().prefetch_related('receipts').order_by('-date')
    
    # Date Filtering
    today = timezone.now().date()
    start_date = None
    end_date = None

    if date_preset:
        if date_preset == 'today':
            start_date = today
        elif date_preset == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = start_date
        elif date_preset == 'last_7':
            start_date = today - timedelta(days=7)
        elif date_preset == 'last_30':
            start_date = today - timedelta(days=30)
        elif date_preset == 'this_month':
            start_date = today.replace(day=1)
        elif date_preset == 'last_month':
            last_month_end = today.replace(day=1) - timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            end_date = last_month_end

    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            pass
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            pass

    if start_date:
        invoices = invoices.filter(date__date__gte=start_date)
    if end_date:
        invoices = invoices.filter(date__date__lte=end_date)
    
    if query:
        invoices = invoices.filter(
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query) |
            Q(id__icontains=query.replace('#', ''))
        )
    
    if paid_filter:
        invoices = invoices.filter(payment_status=paid_filter)
        
    if method_filter:
        invoices = invoices.filter(payment_method=method_filter)
        
    return render(request, 'dashboard/invoices.html', {
        'invoices': invoices,
        'query': query,
        'paid_filter': paid_filter,
        'method_filter': method_filter,
        'date_preset': date_preset,
        'date_from': date_from,
        'date_to': date_to
    })

@login_required
def edit_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        payment_method = request.POST.get('payment_method')
        date_str = request.POST.get('date')
        
        if customer_name:
            # Audit log for changes
            changes = []
            if invoice.customer_name != customer_name:
                changes.append(f"اسم العميل: {invoice.customer_name} -> {customer_name}")
            if invoice.customer_phone != customer_phone:
                changes.append(f"رقم الهاتف: {invoice.customer_phone} -> {customer_phone}")
            
            invoice.customer_name = customer_name
            invoice.customer_phone = customer_phone
            invoice.payment_method = payment_method
            if date_str:
                try:
                    invoice.date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
                except ValueError: pass
            
            # Line item editing
            subtotals = []
            profits = []
            for item in invoice.items.all():
                qty = int(request.POST.get(f'qty_{item.id}', item.quantity))
                price = Decimal(request.POST.get(f'price_{item.id}', item.unit_price))
                cost = Decimal(request.POST.get(f'cost_{item.id}', item.cost_price))
                
                if item.quantity != qty or item.unit_price != price or item.cost_price != cost:
                    changes.append(f"منتج {item.product.name}: تعديل (السعر: {item.unit_price}->{price}, التكلفة: {item.cost_price}->{cost}, الكمية: {item.quantity}->{qty})")
                
                item.quantity = qty
                item.unit_price = price
                item.cost_price = cost
                item.save() # Triggers re-calc in model save()
                
                subtotals.append(item.subtotal)
                profits.append(item.profit)
            
            invoice.total_amount = sum(subtotals) or Decimal('0.00')
            invoice.total_profit = sum(profits) or Decimal('0.00')
            invoice.save()
            
            if changes:
                InvoiceAudit.objects.create(
                    invoice=invoice,
                    action="تعديل بيانات الفاتورة",
                    details=" | ".join(changes)
                )
            
            messages.success(request, "تم تحديث الفاتورة والأسعار.")
            return redirect('invoice_list')
        else:
            messages.error(request, "اسم العميل مطلوب.")
            
    return render(request, 'dashboard/edit_invoice.html', {'invoice': invoice})

@login_required
@require_POST
def delete_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.is_deleted = True
    invoice.deleted_at = timezone.now()
    invoice.deleted_by = request.user.username
    invoice.save()
    
    InvoiceAudit.objects.create(
        invoice=invoice,
        action="حذف الفاتورة",
        details=f"تم الحذف بواسطة {request.user.username} في {invoice.deleted_at}"
    )

    AuditLog.objects.create(
        action="حذف فاتورة",
        entity_type="Invoice",
        entity_id=invoice.id,
        details=f"بواسطة {request.user.username}. عميل: {invoice.customer_name}",
        user=request.user.username
    )
    
    messages.info(request, "تم حذف الفاتورة بنجاح.")
    return redirect('invoice_list')

@login_required
@require_POST
def add_receipt(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if invoice.payment_status == 'paid' or invoice.remaining_balance <= 0:
        messages.error(request, "الفاتورة خالصة بالكامل. لا يمكن إصدار إيصال قبض جديد.")
        return redirect('invoice_view', invoice_id=invoice.id)
        
    amount_str = request.POST.get('amount')
    notes = request.POST.get('notes', '').strip()
    
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            messages.error(request, "يجب أن يكون المبلغ أكبر من صفر.")
        elif amount > invoice.remaining_balance:
            messages.error(request, f"لا يمكن تجاوز المبلغ المتبقي ({invoice.remaining_balance} د.ل).")
        else:
            receipt = Receipt.objects.create(
                invoice=invoice,
                amount=amount,
                notes=notes
            )
            
            # Auto-update status
            if invoice.remaining_balance <= 0:
                invoice.payment_status = 'paid'
            elif invoice.payment_status == 'pending':
                invoice.payment_status = 'unpaid' # Transition from pending once payment starts
            invoice.save()
            
            InvoiceAudit.objects.create(
                invoice=invoice,
                action="إصدار إيصال قبض",
                details=f"قيمة الإيصال: {amount} د.ل | المبلغ المتبقي: {invoice.remaining_balance} د.ل"
            )
            
            messages.success(request, f"تم إصدار الإيصال بنجاح. المتبقي: {invoice.remaining_balance} د.ل")
    except (InvalidOperation, ValueError):
        messages.error(request, "خطأ في مبلغ الإيصال.")
        
    return redirect('invoice_view', invoice_id=invoice.id)

@login_required
def receipt_view(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    return render(request, 'main/receipt_print.html', {'receipt': receipt})

@login_required
@require_POST
def cancel_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    invoice = receipt.invoice
    receipt.is_cancelled = True
    receipt.save()
    
    # Recalculate status
    if invoice.payment_status == 'paid' and invoice.remaining_balance > 0:
        invoice.payment_status = 'unpaid'
    invoice.save()
    
    InvoiceAudit.objects.create(
        invoice=invoice,
        action="إلغاء إيصال قبض",
        details=f"تم إلغاء الإيصال رقم {receipt.id} بقيمة {receipt.amount} د.ل | المبلغ المتبقي: {invoice.remaining_balance} د.ل"
    )

    AuditLog.objects.create(
        action="إلغاء إيصال قبض",
        entity_type="Receipt",
        entity_id=receipt.id,
        details=f"إلغاء إيصال بقيمة {receipt.amount} للفاتورة #{invoice.id}",
        user=request.user.username
    )
    
    messages.info(request, "تم إلغاء الإيصال وتحديث الرصيد.")
    return redirect('invoice_view', invoice_id=invoice.id)

@login_required
@require_POST
def delete_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    invoice = receipt.invoice
    amount = receipt.amount
    
    InvoiceAudit.objects.create(
        invoice=invoice,
        action="حذف إيصال قبض نهائياً",
        details=f"تم حذف إيصال بقيمة {amount} د.ل"
    )

    AuditLog.objects.create(
        action="حذف إيصال قبض نهائياً",
        entity_type="Receipt",
        entity_id=receipt_id,
        details=f"حذف إيصال بقيمة {amount} للفاتورة #{invoice.id}",
        user=request.user.username
    )
    
    receipt.delete()
    
    # Recalculate status
    if invoice.payment_status == 'paid' and invoice.remaining_balance > 0:
        invoice.payment_status = 'unpaid'
    invoice.save()
    
    messages.success(request, "تم حذف الإيصال نهائياً وتحديث الرصيد.")
    return redirect('invoice_view', invoice_id=invoice.id)

@login_required
@admin_required
def sales_view(request):
    query = request.GET.get('q')
    date_preset = request.GET.get('date_preset')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    invoices = Invoice.objects.filter(is_deleted=False).order_by('-date')
    
    # Date Filtering (same logic as invoice_list)
    today = timezone.now().date()
    start_date = None
    end_date = None

    if date_preset:
        if date_preset == 'today':
            start_date = today
        elif date_preset == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = start_date
        elif date_preset == 'last_7':
            start_date = today - timedelta(days=7)
        elif date_preset == 'last_30':
            start_date = today - timedelta(days=30)
        elif date_preset == 'this_month':
            start_date = today.replace(day=1)
        elif date_preset == 'last_month':
            last_month_end = today.replace(day=1) - timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            end_date = last_month_end

    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError: pass
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError: pass

    if start_date:
        invoices = invoices.filter(date__date__gte=start_date)
    if end_date:
        invoices = invoices.filter(date__date__lte=end_date)
    
    if query:
        invoices = invoices.filter(
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query) |
            Q(id__icontains=query.replace('#', ''))
        )
    
    # Financial Summary (Optimized)
    invoices_for_calc = invoices.exclude(payment_status='pending').prefetch_related('items')
    total_sales = Receipt.objects.filter(invoice__in=invoices_for_calc, is_cancelled=False).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_cost = Decimal('0.00')
    for inv in invoices_for_calc:
        total_cost += sum((item.cost_price * item.quantity) for item in inv.items.all())
            
    total_profit = total_sales - total_cost

    return render(request, 'dashboard/sales.html', {
        'invoices': invoices,
        'total_sales': total_sales,
        'total_profit': total_profit,
        'query': query,
        'date_preset': date_preset,
        'date_from': date_from,
        'date_to': date_to,
    })

import openpyxl # type: ignore
from openpyxl.styles import Font, Alignment, PatternFill # type: ignore

@login_required
def export_sales_csv(request):
    invoices = Invoice.objects.filter(is_deleted=False).order_by('-date')
    
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"
    sheet.sheet_view.rightToLeft = True # For Arabic RTL display

    headers = ['رقم الفاتورة', 'العميل', 'التاريخ', 'القيمة الإجمالية', 'المبلغ المدفوع (أرباح/مبيعات)', 'طريقة الدفع', 'الحالة']
    sheet.append(headers)
    
    header_fill = PatternFill(start_color="1A1D2E", end_color="1A1D2E", fill_type="solid")
    header_font = Font(color="D4A745", bold=True)
    
    for col_num, cell in enumerate(sheet[1], 1):
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        sheet.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20
    
    for inv in invoices:
        if inv.payment_status == 'paid':
            status = "خالص"
        elif inv.payment_status == 'unpaid':
            status = "غير خالص"
        else:
            status = "معلقة"
            
        method = "نقد" if inv.payment_method == 'cash' else "بطاقة" if inv.payment_method == 'card' else "تحويل"
        
        row_data = [
            f"#{inv.id}",
            inv.customer_name,
            inv.date.strftime('%Y-%m-%d %H:%M'),
            float(inv.total_amount),
            float(inv.total_paid),
            method,
            status
        ]
        sheet.append(row_data)

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(horizontal='center')

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f'sales_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    workbook.save(response)
    return response

@login_required
@admin_required
def financial_analysis_view(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    payment_method = request.GET.get('method')
    
    # Base queryset for non-deleted invoices, excluding pending ones
    invoices_base = Invoice.objects.filter(is_deleted=False).exclude(payment_status='pending')
    
    # Filtering
    if date_from:
        invoices_base = invoices_base.filter(date__date__gte=date_from)
    if date_to:
        invoices_base = invoices_base.filter(date__date__lte=date_to)
    if payment_method:
        invoices_base = invoices_base.filter(payment_method=payment_method)
    
    # Calculations
    # 1. Total Expenses (Always counted for non-deleted invoices)
    expenses_data = InvoiceItem.objects.filter(invoice__in=invoices_base).aggregate(
        total_expenses=Sum(F('cost_price') * F('quantity'))
    )
    total_expenses = expenses_data['total_expenses'] or Decimal('0.00')
    
    # 2. Total Revenue (ALL collected cash from non-canceled receipts of non-pending invoices)
    receipts_data = Receipt.objects.filter(invoice__in=invoices_base, is_cancelled=False).aggregate(
        total_revenue=Sum('amount')
    )
    total_revenue = receipts_data['total_revenue'] or Decimal('0.00')
    
    # 3. Internal Purchases (Company & Personal Expenses)
    purchases_base = InternalPurchase.objects.all()
    if date_from:
        purchases_base = purchases_base.filter(date__date__gte=date_from)
    if date_to:
        purchases_base = purchases_base.filter(date__date__lte=date_to)
        
    company_expenses = purchases_base.filter(expense_type='company').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    personal_expenses = purchases_base.filter(expense_type='personal').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # 4. Net Profit (Actual Cash Collected - Inventory Cost - Company Expenses)
    # COGS (total_expenses) is already calculated from InvoiceItems.
    # We subtract company overhead/expenses to get the true net profit.
    net_profit = total_revenue - total_expenses - company_expenses
    
    # 4. Profit Margin
    margin = Decimal('0.00')
    if total_revenue > 0:
        margin = (net_profit / total_revenue) * 100
    
    # Breakdown for charts/tables
    context = {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'company_expenses': company_expenses,
        'personal_expenses': personal_expenses,
        'net_profit': net_profit,
        'margin': margin.quantize(Decimal('0.01')),
        'date_from': date_from,
        'date_to': date_to,
        'payment_method': payment_method,
    }
    
    return render(request, 'dashboard/financial_analysis.html', context)

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('dashboard')
        return redirect('product_list')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.is_superuser:
                    return redirect('dashboard')
                return redirect('product_list')
            else:
                messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# --- New Feature Views ---

@login_required
@admin_required
def internal_purchase_list(request):
    expense_type = request.GET.get('type')
    purchases = InternalPurchase.objects.all().prefetch_related('items__product').order_by('-date')
    if expense_type:
        purchases = purchases.filter(expense_type=expense_type)
    return render(request, 'dashboard/purchases.html', {
        'purchases': purchases,
        'expense_type': expense_type
    })

@login_required
@admin_required
def create_internal_purchase(request):
    if request.method == 'POST':
        supplier_name = request.POST.get('supplier_name', '').strip()
        expense_type = request.POST.get('expense_type', 'company')
        payment_status = request.POST.get('payment_status', 'unpaid')
        notes = request.POST.get('notes', '').strip()
        
        purchase = InternalPurchase.objects.create(
            supplier_name=supplier_name,
            expense_type=expense_type,
            payment_status=payment_status,
            notes=notes,
            created_by=request.user.username
        )
        
        p_ids = request.POST.getlist('product_id')
        qtys = request.POST.getlist('quantity')
        costs = request.POST.getlist('unit_cost')
        
        total_amount = Decimal('0.00')
        
        for i in range(len(p_ids)):
            if not p_ids[i] or not qtys[i] or not costs[i]: continue
            
            try:
                prod = get_object_or_404(Product, id=p_ids[i])
                qty = int(qtys[i])
                unit_cost = Decimal(costs[i])
                subtotal = qty * unit_cost
                
                InternalPurchaseItem.objects.create(
                    purchase=purchase,
                    product=prod,
                    quantity=qty,
                    unit_cost=unit_cost,
                    subtotal=subtotal
                )
                
                # Weighted Average Cost Calculation
                old_qty = prod.stock_quantity
                old_cost = prod.cost
                
                new_qty = old_qty + qty
                if new_qty > 0:
                    # (Old Total Cost + New Purchase Cost) / New Total Quantity
                    new_cost = ((old_cost * Decimal(old_qty)) + (unit_cost * Decimal(qty))) / Decimal(new_qty)
                    prod.cost = new_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                prod.stock_quantity = new_qty
                prod.save()
                total_amount += subtotal
                
            except (ValueError, InvalidOperation):
                continue
        
        purchase.total_amount = total_amount
        if payment_status == 'paid':
            purchase.total_paid = total_amount
        purchase.save()
        
        messages.success(request, "تم تسجيل الشراء وتحديث المخزون بنجاح.")
        return redirect('purchase_list')
        
    products = Product.objects.all().order_by('name')
    return render(request, 'dashboard/create_purchase.html', {'products': products})

@login_required
@admin_required
def internal_purchase_detail(request, pk):
    purchase = get_object_or_404(InternalPurchase, pk=pk)
    return render(request, 'dashboard/purchase_detail.html', {'purchase': purchase})

@login_required
@admin_required
def debt_list(request):
    # 1. Customer Debts (What others owe us)
    unpaid_invoices = Invoice.objects.filter(is_deleted=False).exclude(payment_status='paid').prefetch_related('receipts')
    
    customer_map = {}
    for inv in unpaid_invoices:
        key = (inv.customer_name, inv.customer_phone)
        if key not in customer_map:
            customer_map[key] = {
                'name': inv.customer_name, 
                'phone': inv.customer_phone, 
                'total_balance': Decimal('0.00'),
                'invoice_count': 0
            }
        customer_map[key]['total_balance'] += inv.remaining_balance
        customer_map[key]['invoice_count'] += 1
        
    # 2. Company Debts (What we owe to suppliers)
    supplier_debts = InternalPurchase.objects.exclude(payment_status='paid').order_by('-date')
    
    total_customer_debt = sum(d['total_balance'] for d in customer_map.values())
    total_company_debt = sum(p.remaining_balance for p in supplier_debts)
    
    return render(request, 'dashboard/debts.html', {
        'customer_debtors': customer_map.values(),
        'supplier_debts': supplier_debts,
        'total_customer_debt': total_customer_debt,
        'total_company_debt': total_company_debt
    })

@login_required
@require_POST
def record_purchase_payment(request, pk):
    purchase = get_object_or_404(InternalPurchase, pk=pk)
    amount_str = request.POST.get('amount')
    try:
        amount = Decimal(amount_str)
        if amount > purchase.remaining_balance:
            messages.error(request, "المبلغ المدفوع يتجاوز الرصيد المتبقي.")
        else:
            purchase.total_paid += amount
            if purchase.remaining_balance <= 0:
                purchase.payment_status = 'paid'
            elif purchase.total_paid > 0:
                purchase.payment_status = 'unpaid' # still unpaid but has progress
            purchase.save()
            messages.success(request, "تم تسجيل الدفعة بنجاح.")
    except (InvalidOperation, ValueError):
        messages.error(request, "خطأ في قيمة المبلغ.")
    return redirect('purchase_list')

from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required

@login_required
@admin_required
def manage_users(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'dashboard/users.html', {'users': users})

@login_required
@admin_required
@require_POST
def add_user(request):
    username = request.POST.get('username')
    email = request.POST.get('email', '')
    password = request.POST.get('password')
    is_admin = request.POST.get('is_admin') == 'on'
    
    if User.objects.filter(username=username).exists():
        messages.error(request, "اسم المستخدم موجود مسبقاً.")
    else:
        user = User.objects.create_user(username=username, email=email, password=password)
        if is_admin:
            user.is_staff = True
            user.is_superuser = True
        user.save()
        messages.success(request, f"تم إضافة المستخدم {username} بنجاح.")
    
    return redirect('manage_users')

@login_required
@admin_required
@require_POST
def delete_user(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    if user_to_delete == request.user:
        messages.error(request, "لا يمكنك حذف حسابك الحالي.")
    else:
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"تم حذف المستخدم {username} بنجاح.")
    return redirect('manage_users')
