# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Productos
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    
    # Movimientos
    path('movements/', views.movement_list, name='movement_list'),
    path('movements/create/', views.stock_movement_create, name='movement_create'),
    
    # Importación CSV
    path('import/', views.csv_import, name='csv_import'),
    
    # Alertas
    path('alerts/', views.low_stock_alerts, name='low_stock_alerts'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Exportación
    path('export/products/', views.export_products_csv, name='export_products'),
    
    # API para gráficos
    path('api/movement-stats/', views.api_movement_stats, name='api_movement_stats'),
    path('api/category-distribution/', views.api_category_distribution, name='api_category_distribution'),
    path('api/stock-alerts/', views.api_stock_alerts, name='api_stock_alerts'),
]
