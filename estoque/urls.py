from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    path('produtos/', views.lista_produtos, name='lista_produtos'),
    path('produtos/novo/', views.novo_produto, name='novo_produto'),
    path('produtos/editar/<int:pk>/', views.editar_produto, name='editar_produto'),
    path('movimentacao/', views.registrar_movimentacao, name='registrar_movimentacao'),
    path('historico/', views.historico_movimentacoes, name='historico_movimentacoes'),
    path('produtos/pdf/', views.rel_produtos_pdf, name='rel_produtos_pdf'),
    path('historico/pdf/', views.rel_movimentacoes_pdf, name='rel_movimentacoes_pdf'),
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nova/', views.nova_categoria, name='nova_categoria'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/excluir/<int:pk>/', views.excluir_categoria, name='excluir_categoria'),
    path('api/produtos/buscar/', views.buscar_produtos, name='buscar_produtos'),
]
