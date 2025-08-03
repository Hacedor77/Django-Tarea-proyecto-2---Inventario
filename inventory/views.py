# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import csv
import io
import json

from .models import Product, Supplier, Category, StockMovement, LowStockAlert
from .forms import (ProductForm, SupplierForm, CategoryForm, StockMovementForm, 
                   ProductFilterForm, CSVImportForm, MovementFilterForm)


@login_required
def api_category_distribution(request):
    categories = Category.objects.annotate(
        product_count=Count('product', filter=Q(product__is_active=True)),
        total_stock=Sum('product__current_stock', filter=Q(product__is_active=True))
    ).values('name', 'product_count', 'total_stock')
    
    return JsonResponse(list(categories), safe=False)

@login_required
def api_stock_alerts(request):
    alerts = Product.objects.filter(
        is_active=True,
        current_stock__lte=F('minimum_stock')
    ).values('name', 'current_stock', 'minimum_stock')
    
    return JsonResponse(list(alerts), safe=False)

@login_required
def dashboard(request):
    # Estadísticas generales
    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(
        is_active=True, 
        current_stock__lte=F('minimum_stock')
    ).count()
    out_of_stock = Product.objects.filter(is_active=True, current_stock=0).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    
    # Movimientos recientes
    recent_movements = StockMovement.objects.select_related('product', 'created_by')[:10]
    
    # Productos con stock bajo
    low_stock_list = Product.objects.filter(
        is_active=True,
        current_stock__lte=F('minimum_stock')
    ).select_related('category', 'supplier')[:5]
    
    # Datos para gráficos (últimos 7 días)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=6)
    
    # Movimientos por día
    daily_movements = []
    for i in range(7):
        date = start_date + timedelta(days=i)
        movements = StockMovement.objects.filter(
            created_at__date=date
        ).aggregate(
            entries=Count('id', filter=Q(movement_type='IN')),
            exits=Count('id', filter=Q(movement_type='OUT'))
        )
        daily_movements.append({
            'date': date.strftime('%Y-%m-%d'),
            'entries': movements['entries'] or 0,
            'exits': movements['exits'] or 0
        })
    
    context = {
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock': out_of_stock,
        'total_suppliers': total_suppliers,
        'recent_movements': recent_movements,
        'low_stock_list': low_stock_list,
        'daily_movements': json.dumps(daily_movements),
    }
    
    return render(request, 'inventory/dashboard.html', context)

@login_required
def product_list(request):
    form = ProductFilterForm(request.GET)
    products = Product.objects.select_related('category', 'supplier').filter(is_active=True)
    
    if form.is_valid():
        if form.cleaned_data['category']:
            products = products.filter(category=form.cleaned_data['category'])
        
        if form.cleaned_data['supplier']:
            products = products.filter(supplier=form.cleaned_data['supplier'])
        
        if form.cleaned_data['stock_status']:
            status = form.cleaned_data['stock_status']
            if status == 'low':
                products = products.filter(current_stock__lte=F('minimum_stock'))
            elif status == 'out':
                products = products.filter(current_stock=0)
            elif status == 'normal':
                products = products.filter(current_stock__gt=F('minimum_stock')).filter(current_stock__gt=0)


        
        if form.cleaned_data['search']:
            search = form.cleaned_data['search']
            products = products.filter(
                Q(code__icontains=search) | Q(name__icontains=search)
            )
    
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'products': page_obj,
    }
    
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto creado exitosamente.')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'title': 'Crear producto'
    })

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Editar producto'
    })

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    movements = StockMovement.objects.filter(product=product).select_related('created_by')[:20]
    
    context = {
        'product': product,
        'movements': movements,
    }
    
    return render(request, 'inventory/product_detail.html', context)

@login_required
def stock_movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    movement = form.save(commit=False)
                    movement.created_by = request.user
                    movement.save()
                    
                    # Crear alerta si el stock está bajo
                    product = movement.product
                    if product.is_low_stock:
                        LowStockAlert.objects.get_or_create(
                            product=product,
                            is_resolved=False,
                            defaults={
                                'current_stock': product.current_stock,
                                'minimum_stock': product.minimum_stock
                            }
                        )
                    
                    messages.success(request, 'Movimiento registrado exitosamente.')
                    return redirect('movement_list')
            
            except ValidationError as e:
                form.add_error(None, str(e))
            except Exception as e:
                messages.error(request, f'Error al registrar movimiento: {str(e)}')
    else:
        form = StockMovementForm()
    
    return render(request, 'inventory/movement_form.html', {
        'form': form,
        'title': 'Registrar movimiento'
    })

@login_required
def movement_list(request):
    form = MovementFilterForm(request.GET)
    movements = StockMovement.objects.select_related(
        'product', 'product__category', 'created_by'
    ).all()
    
    if form.is_valid():
        if form.cleaned_data['product']:
            movements = movements.filter(product=form.cleaned_data['product'])
        
        if form.cleaned_data['movement_type']:
            movements = movements.filter(movement_type=form.cleaned_data['movement_type'])
        
        if form.cleaned_data['date_from']:
            movements = movements.filter(created_at__date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data['date_to']:
            movements = movements.filter(created_at__date__lte=form.cleaned_data['date_to'])
    
    paginator = Paginator(movements, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'movements': page_obj,
    }
    
    return render(request, 'inventory/movement_list.html', context)

@login_required
def csv_import(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                with transaction.atomic():
                    content = csv_file.read().decode('utf-8')
                    csv_reader = csv.DictReader(io.StringIO(content))
                    
                    created_count = 0
                    updated_count = 0
                    errors = []
                    
                    for row_num, row in enumerate(csv_reader, start=2):
                        try:
                            # Obtener o crear categoría
                            category, _ = Category.objects.get_or_create(
                                name=row['category']
                            )
                            
                            # Obtener o crear proveedor
                            supplier, _ = Supplier.objects.get_or_create(
                                name=row['supplier']
                            )
                            
                            # Crear o actualizar producto
                            product_data = {
                                'name': row['name'],
                                'description': row.get('description', ''),
                                'category': category,
                                'supplier': supplier,
                                'unit_price': float(row['unit_price']),
                                'minimum_stock': int(row.get('minimum_stock', 10)),
                                'maximum_stock': int(row.get('maximum_stock', 1000)),
                                'current_stock': int(row.get('current_stock', 0)),
                            }
                            
                            product, created = Product.objects.update_or_create(
                                code=row['code'],
                                defaults=product_data
                            )
                            
                            if created:
                                created_count += 1
                            else:
                                updated_count += 1
                        
                        except Exception as e:
                            errors.append(f"Fila {row_num}: {str(e)}")
                    
                    if errors:
                        messages.warning(
                            request, 
                            f'Importación completada con errores. Creados: {created_count}, '
                            f'Actualizados: {updated_count}. Errores: {"; ".join(errors[:5])}'
                        )
                    else:
                        messages.success(
                            request,
                            f'Importación exitosa. Creados: {created_count}, '
                            f'Actualizados: {updated_count}'
                        )
                    
                    return redirect('product_list')
            
            except Exception as e:
                messages.error(request, f'Error al procesar archivo: {str(e)}')
    else:
        form = CSVImportForm()
    
    return render(request, 'inventory/csv_import.html', {'form': form})

@login_required
def low_stock_alerts(request):
    alerts = LowStockAlert.objects.filter(is_resolved=False).select_related('product')
    
    return render(request, 'inventory/low_stock_alerts.html', {
        'alerts': alerts
    })

@login_required
def resolve_alert(request, alert_id):
    if request.method == 'POST':
        alert = get_object_or_404(LowStockAlert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        
        messages.success(request, 'Alerta resuelta.')
    
    return redirect('low_stock_alerts')

@login_required
def export_products_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="productos.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Código', 'Nombre', 'Descripción', 'Categoría', 'Proveedor',
        'Precio unitario', 'Stock actual', 'Stock mínimo', 'Stock máximo'
    ])
    
    products = Product.objects.select_related('category', 'supplier').filter(is_active=True)
    for product in products:
        writer.writerow([
            product.code,
            product.name,
            product.description,
            product.category.name,
            product.supplier.name,
            product.unit_price,
            product.current_stock,
            product.minimum_stock,
            product.maximum_stock,
        ])
    
    return response

# API endpoints para gráficos
@login_required
def api_movement_stats(request):
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    movements = StockMovement.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date', 'movement_type').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    )
    
    data = {}
    for movement in movements:
        date_str = movement['created_at__date'].strftime('%Y-%m-%d')
        if date_str not in data:
            data[date_str] = {'IN': 0, 'OUT': 0}
        data[date_str][movement['movement_type']] = movement['total_quantity']
    
    return JsonResponse(data)

@login_required
def api_product_stock(request):
    products = Product.objects.filter(is_active=True).values(
        'code', 'name', 'current_stock', 'minimum_stock'
    )
    
    return JsonResponse(list(products), safe=False)

