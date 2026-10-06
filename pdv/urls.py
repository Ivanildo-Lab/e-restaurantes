from django.urls import path
from . import views

app_name = 'pdv'

urlpatterns = [
    path('', views.nova_venda, name='nova_venda'),
    path('historico/', views.historico_vendas, name='historico_vendas'),
    path('historico/pdf/', views.rel_vendas_pdf, name='rel_vendas_pdf'),
    path('<int:venda_id>/', views.venda_aberta, name='venda_aberta'),
    path('<int:venda_id>/adicionar-item/', views.adicionar_item, name='adicionar_item'),
    path('item/<int:item_id>/remover/', views.remover_item, name='remover_item'),
    path('<int:venda_id>/finalizar/', views.finalizar_venda, name='finalizar_venda'),
    path('<int:venda_id>/recibo/', views.recibo_venda, name='recibo_venda'),
    path('<int:venda_id>/cancelar/', views.cancelar_venda, name='cancelar_venda'),
]
