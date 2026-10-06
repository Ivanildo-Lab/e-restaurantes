from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from cadastros.models import Cadastro
from estoque.models import Produto
from financeiro.models import PlanoDeContas, Caixa


@login_required
def buscar_cadastro(request):
    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    queryset = Cadastro.objects.filter(empresa=empresa, situacao='ATIVO')
    if q:
        queryset = queryset.filter(nome__icontains=q)[:20]
    else:
        queryset = queryset.all()[:20]
    results = [{'id': c.id, 'text': f'{c.nome} ({c.get_papel_display()})'} for c in queryset]
    return JsonResponse({'results': results})


@login_required
def buscar_produto(request):
    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    queryset = Produto.objects.filter(empresa=empresa)
    if q:
        queryset = queryset.filter(nome__icontains=q)[:20]
    else:
        queryset = queryset.all()[:20]
    results = [{'id': p.id, 'text': f'{p} - R$ {p.preco_venda}'} for p in queryset]
    return JsonResponse({'results': results})


@login_required
def buscar_plano_contas(request):
    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    tipo = request.GET.get('tipo')
    queryset = PlanoDeContas.objects.filter(empresa=empresa)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if q:
        queryset = queryset.filter(nome__icontains=q)[:20]
    else:
        queryset = queryset.all()[:20]
    results = [{'id': p.id, 'text': f'{p.codigo} - {p.nome}'} for p in queryset]
    return JsonResponse({'results': results})


@login_required
def buscar_caixa(request):
    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    queryset = Caixa.objects.filter(empresa=empresa)
    if q:
        queryset = queryset.filter(nome__icontains=q)[:20]
    else:
        queryset = queryset.all()[:20]
    results = [{'id': c.id, 'text': c.nome} for c in queryset]
    return JsonResponse({'results': results})
