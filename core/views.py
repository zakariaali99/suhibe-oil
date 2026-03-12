import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Company, Density, Product, Invoice, InvoiceItem
from decimal import Decimal
import io

# PDF generation imports
from weasyprint import HTML
import arabic_reshaper
from bidi.algorithm import get_display

# --- POS Views ---

def product_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.all()
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(company__name__icontains=query) | 
            Q(density__value__icontains=query)
        )
    
    # Simple cart management in session
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

def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    cart[product_id_str] = cart.get(product_id_str, 0) + 1
    request.session['cart'] = cart
    messages.success(request, "تمت إضافة المنتج للعربة successfully.")
    return redirect('product_list')

def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        messages.info(request, "تمت إزالة المنتج من العربة.")
    return redirect('product_list')

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
        customer_name = request.POST.get('customer_name')
        payment_method = request.POST.get('payment_method')
        is_paid = request.POST.get('is_paid') == 'on'
        
        # Create Invoice
        invoice = Invoice.objects.create(
            customer_name=customer_name,
            payment_method=payment_method,
            is_paid=is_paid
        )
        
        total = Decimal('0.00')
        for item in products_in_cart:
            pid = str(item['product'].id)
            price = Decimal(request.POST.get(f'price_{pid}', '0.00'))
            qty = int(request.POST.get(f'qty_{pid}', item['quantity']))
            
            subtotal = price * qty
            InvoiceItem.objects.create(
                invoice=invoice,
                product=item['product'],
                quantity=qty,
                unit_price=price,
                subtotal=subtotal
            )
            total += subtotal
        
        invoice.total_amount = total
        invoice.save()
        
        # Clear cart
        request.session['cart'] = {}
        
        return redirect('invoice_view', invoice_id=invoice.id)

    return render(request, 'main/checkout.html', {
        'products_in_cart': products_in_cart
    })

def invoice_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'main/invoice.html', {'invoice': invoice})

def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Reshape Arabic text for PDF
    def reshape_text(text):
        if not text: return ""
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text

    # We'll handle reshaping in the template or here
    # For simplicity, we'll try to use a font that handles RTL well in WeasyPrint
    
    html_string = render_to_string('pdf/invoice_pdf.html', {'invoice': invoice})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'
    return response

# --- Dashboard Views ---

def dashboard(request):
    return render(request, 'dashboard/index.html')

def manage_companies(request):
    companies = Company.objects.all().order_by('-created_at')
    return render(request, 'dashboard/companies.html', {'companies': companies})

def add_company(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        Company.objects.create(name=name)
        messages.success(request, "تمت إضافة الشركة.")
    return redirect('manage_companies')

def delete_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.delete()
    messages.info(request, "تم حذف الشركة.")
    return redirect('manage_companies')

def manage_densities(request):
    densities = Density.objects.all().order_by('-created_at')
    return render(request, 'dashboard/densities.html', {'densities': densities})

def add_density(request):
    if request.method == 'POST':
        value = request.POST.get('value')
        Density.objects.create(value=value)
        messages.success(request, "تمت إضافة الكثافة.")
    return redirect('manage_densities')

def delete_density(request, pk):
    density = get_object_or_404(Density, pk=pk)
    density.delete()
    messages.info(request, "تم حذف الكثافة.")
    return redirect('manage_densities')

def manage_products(request):
    products = Product.objects.all().order_by('-created_at')
    companies = Company.objects.all()
    densities = Density.objects.all()
    return render(request, 'dashboard/products.html', {
        'products': products,
        'companies': companies,
        'densities': densities
    })

def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        company_id = request.POST.get('company_id')
        density_id = request.POST.get('density_id')
        Product.objects.create(
            name=name,
            company_id=company_id,
            density_id=density_id
        )
        messages.success(request, "تمت إضافة المنتج.")
    return redirect('manage_products')

def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.info(request, "تم حذف المنتج.")
    return redirect('manage_products')

def invoice_list(request):
    payment_method = request.GET.get('payment_method')
    is_paid = request.GET.get('is_paid')
    
    invoices = Invoice.objects.all().order_by('-date')
    
    if payment_method:
        invoices = invoices.filter(payment_method=payment_method)
    if is_paid:
        invoices = invoices.filter(is_paid=(is_paid == '1'))
        
    return render(request, 'dashboard/invoices.html', {
        'invoices': invoices,
        'payment_method': payment_method,
        'is_paid': is_paid
    })

def toggle_invoice_paid(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.is_paid = not invoice.is_paid
    invoice.save()
    messages.success(request, "تم تحديث حالة الدفع.")
    return redirect('invoice_list')
