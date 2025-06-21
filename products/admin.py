from django.contrib import admin
from .models import *

# Register your models here.


admin.site.register(Category)
admin.site.register(Coupon)

class ProductImageAdmin(admin.StackedInline):
    model = ProductImage


class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'price']
    inlines = [ProductImageAdmin]


@admin.register(ColorVariant)
class ColorVariantAdmin(admin.ModelAdmin):
    list_display = ['color_name', 'price']
    model = ColorVariant


@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ['size_name', 'price', 'order']

    model = SizeVariant


admin.site.register(ProductImage)
admin.site.register(ProductReview)

admin.site.register(Product, ProductAdmin)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'is_trending', 'newest_product')
    list_editable = ('is_trending', 'newest_product')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)  # Customize fields to show in admin list view