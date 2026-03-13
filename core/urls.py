from django.urls import path
from . import views

urlpatterns = [
    # POS Flow
    path('', views.product_list, name='product_list'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/<str:action>/', views.update_cart_qty, name='update_cart_qty'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('invoice/<int:invoice_id>/', views.invoice_view, name='invoice_view'),
    path('invoice/<int:invoice_id>/invoice.pdf', views.invoice_pdf, name='invoice_pdf'),

    # Dashboard
    path('manage/', views.dashboard, name='dashboard'),
    
    path('manage/companies/', views.manage_companies, name='manage_companies'),
    path('manage/companies/add/', views.add_company, name='add_company'),
    path('manage/companies/edit/<int:pk>/', views.edit_company, name='edit_company'),
    path('manage/companies/delete/<int:pk>/', views.delete_company, name='delete_company'),
    
    path('manage/densities/', views.manage_densities, name='manage_densities'),
    path('manage/densities/add/', views.add_density, name='add_density'),
    path('manage/densities/edit/<int:pk>/', views.edit_density, name='edit_density'),
    path('manage/densities/delete/<int:pk>/', views.delete_density, name='delete_density'),
    
    path('manage/products/', views.manage_products, name='manage_products'),
    path('manage/products/add/', views.add_product, name='add_product'),
    path('manage/products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('manage/products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    
    path('manage/invoices/', views.invoice_list, name='invoice_list'),
    path('manage/invoices/<int:pk>/toggle-paid/', views.toggle_invoice_paid, name='toggle_invoice_paid'),
]
