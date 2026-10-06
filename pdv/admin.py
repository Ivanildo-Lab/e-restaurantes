from django.contrib import admin
from .models import Venda, ItemVenda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = ('subtotal',)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'data_venda', 'valor_total', 'forma_pagamento', 'status')
    list_filter = ('status', 'forma_pagamento')
    inlines = [ItemVendaInline]


admin.site.register(ItemVenda)
