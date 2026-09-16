from django.contrib import admin
from .models import PlanoDeContas, Caixa, Conta, Lancamento, FormaPagamento

admin.site.register(PlanoDeContas)
admin.site.register(Caixa)
admin.site.register(Conta)
admin.site.register(Lancamento)
admin.site.register(FormaPagamento)
