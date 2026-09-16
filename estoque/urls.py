from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    path('produtos/', views.lista_produtos, name='lista_produtos'),
    path('produtos/novo/', views.novo_produto, name='novo_produto'),
    path('produtos/editar/<int:pk>/', views.editar_produto, name='editar_produto'),
    path('movimentacao/', views.registrar_movimentacao, name='registrar_movimentacao'),
    path('api/produtos/buscar/', views.buscar_produtos, name='buscar_produtos'),
]
