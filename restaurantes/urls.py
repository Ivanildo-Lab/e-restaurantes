from django.urls import path
from . import views

app_name = 'restaurantes'

urlpatterns = [
    path('', views.mapa_mesas, name='mapa_mesas'),
    path('abrir/<int:mesa_id>/', views.abrir_mesa, name='abrir_mesa'),
    path('<int:mesa_id>/', views.mesa_aberta, name='mesa_aberta'),
    path('<int:mesa_id>/adicionar-item/', views.adicionar_item, name='adicionar_item'),
    path('item/<int:item_id>/remover/', views.remover_item, name='remover_item'),
    path('<int:mesa_id>/fechar/', views.fechar_mesa, name='fechar_mesa'),
    path('<int:mesa_id>/comprovante/', views.comprovante_mesa, name='comprovante_mesa'),
    path('gerenciar/', views.gerenciar_mesas, name='gerenciar_mesas'),
    path('gerenciar/<int:mesa_id>/editar/', views.editar_mesa, name='editar_mesa'),
    path('gerenciar/<int:mesa_id>/excluir/', views.excluir_mesa, name='excluir_mesa'),
]
