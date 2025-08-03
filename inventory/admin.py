# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from .models import Category, Supplier, Product, StockMovement, LowStockAlert

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'product_count', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    ordering = ['name']

    def product_count(self, obj):
        return obj.product_set.filter(is_active=True).count()
    product_count.short_description = 'Productos activos'

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'is_active', 'product_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'email']
    list_editable = ['is_active']
    ordering = ['name']

    def product_count(self, obj):
        return obj.product_set.filter(is_active=True).count()
    product_count.short_description = 'Productos'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'category', 'supplier', 'current_stock', 
        'minimum_stock', 'stock_status_display', 'unit_price', 'is_active'
    ]
    list_filter = ['category', 'supplier', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    list_editable = ['minimum_stock', 'is_active']
    ordering = ['name']
    readonly_fields = ['current_stock', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información básica', {
            'fields': ('code', 'name', 'description', 'category', 'supplier')
        }),
        ('Precio y stock', {
            'fields': ('unit_price', 'current_stock', 'minimum_stock', 'maximum_stock')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stock_status_display(self, obj):
        if obj.current_stock == 0:
            return format_html('<span style="color: red;">Sin stock</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color: orange;">Stock bajo</span>')
        else:
            return format_html('<span style="color: green;">Stock normal</span>')
    stock_status_display.short_description = 'Estado del stock'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'supplier')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'movement_type', 'quantity', 'unit_price', 
        'total_value', 'created_by', 'created_at'
    ]
    list_filter = ['movement_type', 'created_at', 'product__category']
    search_fields = ['product__name', 'product__code', 'reference', 'notes']
    readonly_fields = ['created_at', 'previous_stock', 'new_stock', 'total_value']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Movimiento', {
            'fields': ('product', 'movement_type', 'quantity')
        }),
        ('Precios', {
            'fields': ('unit_price', 'total_value')
        }),
        ('Información adicional', {
            'fields': ('reference', 'notes')
        }),
        ('Stock', {
            'fields': ('previous_stock', 'new_stock'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'product__category', 'created_by'
        )

    def save_model(self, request, obj, form, change):
        if not change:  # Solo en creación
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'current_stock', 'minimum_stock', 
        'is_resolved', 'created_at', 'resolved_at'
    ]
    list_filter = ['is_resolved', 'created_at']
    search_fields = ['product__name', 'product__code']
    readonly_fields = ['created_at', 'resolved_at']
    ordering = ['-created_at']
    
    actions = ['mark_as_resolved']

    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_resolved=True, resolved_at=timezone.now())
        self.message_user(
            request, 
            f'{updated} alertas marcadas como resueltas.'
        )
    mark_as_resolved.short_description = 'Marcar como resueltas'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')