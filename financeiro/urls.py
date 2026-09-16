from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('fluxo/', views.fluxo_caixa, name='fluxo_caixa'),
    path('fluxo/novo/', views.novo_lancamento_manual, name='adicionar_lancamento'),
    path('fluxo/editar/<int:id>/', views.editar_lancamento, name='editar_lancamento'),
    path('fluxo/excluir/<int:id>/', views.excluir_lancamento, name='excluir_lancamento'),
    path('contas/receber/', views.lista_contas_receber, name='lista_receber'),
    path('contas/receber/nova/', views.nova_receita, name='nova_receita'),
    path('contas/pagar/', views.lista_contas_pagar, name='lista_pagar'),
    path('contas/pagar/nova/', views.nova_despesa, name='nova_despesa'),
    path('contas/baixar/<int:id>/', views.baixar_conta, name='baixar_conta'),
    path('contas/editar/<int:id>/', views.editar_conta, name='editar_conta'),
    path('contas/excluir/<int:id>/', views.excluir_conta, name='excluir_conta'),
    path('caixas/', views.lista_caixas, name='lista_caixas'),
    path('caixas/novo/', views.adicionar_caixa, name='adicionar_caixa'),
    path('caixas/editar/<int:id>/', views.editar_caixa, name='editar_caixa'),
    path('caixas/excluir/<int:id>/', views.excluir_caixa, name='excluir_caixa'),
    path('caixas/set-padrao/<int:id>/', views.definir_caixa_padrao, name='set_caixa_padrao'),
    path('plano-de-contas/', views.lista_plano_de_contas, name='lista_plano_de_contas'),
    path('plano-de-contas/novo/', views.adicionar_plano_de_contas, name='adicionar_plano_de_contas'),
    path('plano-de-contas/editar/<int:id>/', views.editar_plano_de_contas, name='editar_plano_de_contas'),
    path('plano-de-contas/excluir/<int:id>/', views.excluir_plano_de_contas, name='excluir_plano_de_contas'),
    path('formas-pagamento/', views.lista_formas_pagamento, name='lista_formas_pagamento'),
    path('formas-pagamento/nova/', views.nova_forma_pagamento, name='nova_forma_pagamento'),
]
