from django.urls import path  # type: ignore
from . import views  # type: ignore

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
    path('invoice/<int:invoice_id>/receipt/add/', views.add_receipt, name='add_receipt'),
    path('receipt/<int:receipt_id>/', views.receipt_view, name='receipt_view'),
    path('receipt/<int:receipt_id>/cancel/', views.cancel_receipt, name='cancel_receipt'),
    path('receipt/<int:receipt_id>/delete/', views.delete_receipt, name='delete_receipt'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

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
    path('manage/invoices/<int:pk>/edit/', views.edit_invoice, name='edit_invoice'),
    path('manage/invoices/<int:pk>/delete/', views.delete_invoice, name='delete_invoice'),
    
    path('manage/sales/', views.sales_view, name='sales_view'),
    path('manage/financial-analysis/', views.financial_analysis_view, name='financial_analysis'),
    path('manage/sales/export/', views.export_sales_csv, name='export_sales_csv'),

    # New Features
    path('manage/purchases/', views.internal_purchase_list, name='purchase_list'),
    path('manage/purchases/create/', views.create_internal_purchase, name='create_purchase'),
    path('manage/purchases/<int:pk>/', views.internal_purchase_detail, name='purchase_detail'),
    path('manage/purchases/<int:pk>/pay/', views.record_purchase_payment, name='record_purchase_payment'),
    path('manage/debts/', views.debt_list, name='debt_list'),
    path('manage/users/', views.manage_users, name='manage_users'),
    path('manage/users/add/', views.add_user, name='add_user'),
    path('manage/users/delete/<int:pk>/', views.delete_user, name='delete_user'),
]
