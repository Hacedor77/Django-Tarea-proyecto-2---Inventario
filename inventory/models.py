# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="Persona de contacto")
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    address = models.TextField(blank=True, verbose_name="Dirección")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Categoría")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Proveedor")
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Precio unitario"
    )
    current_stock = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name="Stock actual"
    )
    minimum_stock = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        verbose_name="Stock mínimo"
    )
    maximum_stock = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(1)],
        verbose_name="Stock máximo"
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock

    @property
    def stock_status(self):
        if self.current_stock == 0:
            return "Sin stock"
        elif self.current_stock <= self.minimum_stock:
            return "Stock bajo"
        elif self.current_stock >= self.maximum_stock:
            return "Stock alto"
        return "Stock normal"

    def update_stock(self, quantity, movement_type):
        """Actualiza el stock basado en el tipo de movimiento"""
        if movement_type == 'IN':
            self.current_stock += quantity
        elif movement_type == 'OUT':
            if self.current_stock >= quantity:
                self.current_stock -= quantity
            else:
                raise ValueError("Stock insuficiente")
        self.save()

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Entrada'),
        ('OUT', 'Salida'),
        ('ADJ', 'Ajuste'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    movement_type = models.CharField(
        max_length=3, 
        choices=MOVEMENT_TYPES, 
        verbose_name="Tipo de movimiento"
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Precio unitario"
    )
    total_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Valor total"
    )
    reference = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Referencia"
    )
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    previous_stock = models.IntegerField(verbose_name="Stock anterior")
    new_stock = models.IntegerField(default=0, verbose_name="Nuevo stock")

    class Meta:
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} - {self.quantity}"

    def save(self, *args, **kwargs):
        # Validar tipo de movimiento
        if self.movement_type not in ['IN', 'OUT', 'ADJ']:
            raise ValueError("Tipo de movimiento no válido")

        is_new = self.pk is None

        # Calcular valor total si no está establecido
        if self.unit_price and not self.total_value:
            self.total_value = self.unit_price * self.quantity

        # Guardar stock anterior (solo si es nuevo)
        if is_new:
            self.previous_stock = self.product.current_stock

            # Ajustar stock según tipo de movimiento
            if self.movement_type == 'ADJ':
                self.product.current_stock = self.quantity
                self.product.save()
            else:
                try:
                    self.product.update_stock(self.quantity, self.movement_type)
                except ValueError as e:
                    raise ValidationError(str(e))

            # Guardar nuevo stock después de la modificación
            self.new_stock = self.product.current_stock
            
        super().save(*args, **kwargs)

        # Asegurar que new_stock está actualizado en la BD después de guardar
        StockMovement.objects.filter(pk=self.pk).update(new_stock=self.new_stock)       

class LowStockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    current_stock = models.IntegerField()
    minimum_stock = models.IntegerField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Alerta de stock bajo"
        verbose_name_plural = "Alertas de stock bajo"
        ordering = ['-created_at']

    def __str__(self):
        return f"Alerta: {self.product.name} ({self.current_stock}/{self.minimum_stock})"