from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from restaurantes.views import home
from core.api import buscar_cadastro, buscar_produto, buscar_plano_contas, buscar_caixa

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('mesas/', include('restaurantes.urls')),
    path('cadastros/', include('cadastros.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('estoque/', include('estoque.urls')),
    path('pdv/', include('pdv.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/buscar/cadastro/', buscar_cadastro, name='api_buscar_cadastro'),
    path('api/buscar/produto/', buscar_produto, name='api_buscar_produto'),
    path('api/buscar/plano-contas/', buscar_plano_contas, name='api_buscar_plano_contas'),
    path('api/buscar/caixa/', buscar_caixa, name='api_buscar_caixa'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
