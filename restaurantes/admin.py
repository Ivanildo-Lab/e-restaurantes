from django.contrib import admin
from .models import Mesa, ItemMesa, MesaOcupacao

admin.site.register(Mesa)
admin.site.register(ItemMesa)
admin.site.register(MesaOcupacao)
