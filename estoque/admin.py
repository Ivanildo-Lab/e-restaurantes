from django.contrib import admin
from .models import Produto, MovimentacaoEstoque

admin.site.register(Produto)
admin.site.register(MovimentacaoEstoque)
