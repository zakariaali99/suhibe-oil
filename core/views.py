from django.shortcuts import render, redirect, get_object_or_404  # type: ignore
from django.contrib import messages  # type: ignore
from django.db.models import Q, Count  # type: ignore
from django.http import HttpResponse  # type: ignore
from django.template.loader import render_to_string  # type: ignore
from django.views.decorators.http import require_POST  # type: ignore
from .models import Company, Density, Product, Invoice, InvoiceItem  # type: ignore
from decimal import Decimal, InvalidOperation

# PDF generation imports
from xhtml2pdf import pisa  # type: ignore
import io
import os
from django.conf import settings  # type: ignore
from django.contrib.staticfiles import finders  # type: ignore

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

def product_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.all().select_related('company', 'density')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(company__name__icontains=query) | 
            Q(density__value__icontains=query)
        )
    
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total_qty = 0
    for pid, qty in cart.items():
        try:
            prod = Product.objects.get(id=pid)
            cart_items.append({'product': prod, 'quantity': qty})
            cart_total_qty += qty
        except Product.DoesNotExist:
            continue

    return render(request, 'main/product_list.html', {
        'products': products,
        'cart_items': cart_items,
        'cart_total_qty': cart_total_qty,
        'query': query,
    })

@require_POST
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    cart[product_id_str] = cart.get(product_id_str, 0) + 1
    request.session['cart'] = cart
    messages.success(request, "تمت إضافة المنتج للعربة.")
    return redirect('product_list')

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

@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        messages.info(request, "تمت إزالة المنتج من العربة.")
    return redirect('product_list')

@require_POST
def clear_cart(request):
    request.session['cart'] = {}
    return redirect('product_list')

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "العربة فارغة!")
        return redirect('product_list')
    
    products_in_cart = []
    for pid, qty in cart.items():
        prod = get_object_or_404(Product, id=pid)
        products_in_cart.append({'product': prod, 'quantity': qty})

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        payment_method = request.POST.get('payment_method')
        is_paid = request.POST.get('is_paid') == 'on'
        
        if not customer_name:
            messages.error(request, "يرجى إدخال اسم العميل.")
            return render(request, 'main/checkout.html', {'products_in_cart': products_in_cart})

        try:
            # Create Invoice
            invoice = Invoice.objects.create(
                customer_name=customer_name,
                payment_method=payment_method,
                is_paid=is_paid
            )
            
            subtotals = []
            for item in products_in_cart:
                pid = str(item['product'].id)
                price_str = request.POST.get(f'price_{pid}', '0').strip()
                qty_str = request.POST.get(f'qty_{pid}', '1').strip()
                
                try:
                    price = Decimal(price_str) if price_str else Decimal('0.00')
                except InvalidOperation:
                    price = Decimal('0.00')
                
                qty = int(qty_str) if qty_str else 0
                
                if qty <= 0: continue

                subtotal = price * qty
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=item['product'],
                    quantity=qty,
                    unit_price=price,
                    subtotal=subtotal
                )
                subtotals.append(subtotal)
            
            invoice.total_amount = sum(subtotals, Decimal('0.00'))
            invoice.save()
            
            # Clear cart
            request.session['cart'] = {}
            return redirect('invoice_view', invoice_id=invoice.id)
            
        except (InvalidOperation, ValueError):
            messages.error(request, "خطأ في القيم المدخلة (الأسعار أو الكميات).")
            return render(request, 'main/checkout.html', {'products_in_cart': products_in_cart})

    return render(request, 'main/checkout.html', {
        'products_in_cart': products_in_cart
    })

def invoice_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'main/invoice.html', {'invoice': invoice})

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

def dashboard(request):
    stats = {
        'companies': Company.objects.count(),
        'densities': Density.objects.count(),
        'products': Product.objects.count(),
        'invoices': Invoice.objects.count(),
    }
    return render(request, 'dashboard/index.html', {'stats': stats})

# Companies
def manage_companies(request):
    companies = Company.objects.all().order_by('-created_at')
    return render(request, 'dashboard/companies.html', {'companies': companies})

@require_POST
def add_company(request):
    name = request.POST.get('name', '').strip()
    if name:
        Company.objects.create(name=name)
        messages.success(request, "تمت إضافة الشركة.")
    else:
        messages.error(request, "اسم الشركة مطلوب.")
    return redirect('manage_companies')

@require_POST
def edit_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    name = request.POST.get('name', '').strip()
    if name:
        company.name = name
        company.save()
        messages.success(request, "تم تحديث الشركة.")
    return redirect('manage_companies')

@require_POST
def delete_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.delete()
    messages.info(request, "تم حذف الشركة.")
    return redirect('manage_companies')

# Densities
def manage_densities(request):
    densities = Density.objects.all().order_by('-created_at')
    return render(request, 'dashboard/densities.html', {'densities': densities})

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
def edit_density(request, pk):
    density = get_object_or_404(Density, pk=pk)
    value = request.POST.get('value', '').strip()
    if value:
        density.value = value
        density.save()
        messages.success(request, "تم تحديث الكثافة.")
    return redirect('manage_densities')

@require_POST
def delete_density(request, pk):
    density = get_object_or_404(Density, pk=pk)
    density.delete()
    messages.info(request, "تم حذف الكثافة.")
    return redirect('manage_densities')

# Products
def manage_products(request):
    products = Product.objects.all().select_related('company', 'density').order_by('-created_at')
    companies = Company.objects.all()
    densities = Density.objects.all()
    return render(request, 'dashboard/products.html', {
        'products': products,
        'companies': companies,
        'densities': densities
    })

@require_POST
def add_product(request):
    name = request.POST.get('name', '').strip()
    company_id = request.POST.get('company_id')
    density_id = request.POST.get('density_id')
    if name and company_id and density_id:
        Product.objects.create(name=name, company_id=company_id, density_id=density_id)
        messages.success(request, "تمت إضافة المنتج.")
    else:
        messages.error(request, "جميع الحقول مطلوبة.")
    return redirect('manage_products')

@require_POST
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = request.POST.get('name', '').strip()
    company_id = request.POST.get('company_id')
    density_id = request.POST.get('density_id')
    if name and company_id and density_id:
        product.name = name
        product.company_id = company_id
        product.density_id = density_id
        product.save()
        messages.success(request, "تم تحديث المنتج.")
    return redirect('manage_products')

@require_POST
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.info(request, "تم حذف المنتج.")
    return redirect('manage_products')

# Invoices
def invoice_list(request):
    query = request.GET.get('q')
    paid_filter = request.GET.get('paid')
    method_filter = request.GET.get('method')
    
    invoices = Invoice.objects.all().order_by('-date')
    
    if query:
        invoices = invoices.filter(
            Q(customer_name__icontains=query) |
            Q(id__icontains=query.replace('#', ''))
        )
    
    if paid_filter:
        invoices = invoices.filter(is_paid=(paid_filter == '1'))
        
    if method_filter:
        invoices = invoices.filter(payment_method=method_filter)
        
    return render(request, 'dashboard/invoices.html', {
        'invoices': invoices,
        'query': query,
        'paid_filter': paid_filter,
        'method_filter': method_filter
    })

@require_POST
def toggle_invoice_paid(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.is_paid = not invoice.is_paid
    invoice.save()
    messages.success(request, "تم تحديث حالة الدفع.")
    return redirect('invoice_list')
