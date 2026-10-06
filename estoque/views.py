from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from .models import Produto, MovimentacaoEstoque, Categoria
from .forms import ProdutoForm, MovimentacaoForm, CategoriaForm
from datetime import timedelta, date
from financeiro.models import Conta, Lancamento, PlanoDeContas

@login_required
def lista_produtos(request):
    produtos = Produto.objects.filter(empresa=request.user.empresa).select_related('categoria').order_by('categoria__ordem', 'nome')
    
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    categoria_id = request.GET.get('categoria', '')
    
    if q:
        produtos = produtos.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
    if tipo:
        produtos = produtos.filter(tipo=tipo)
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    categorias = Categoria.objects.filter(empresa=request.user.empresa).order_by('ordem', 'nome')
    
    return render(request, 'estoque/lista_produtos.html', {
        'produtos': produtos,
        'categorias': categorias,
        'q': q,
        'tipo': tipo,
        'categoria_id': categoria_id,
    })

@login_required
def novo_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.empresa = request.user.empresa
            p.save()
            messages.success(request, f"Item '{p.nome}' cadastrado!")
            return redirect('estoque:lista_produtos')
    else:
        form = ProdutoForm(user=request.user)
    return render(request, 'estoque/form_produto.html', {'form': form, 'titulo': 'Novo Item'})

@login_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Item atualizado!")
            return redirect('estoque:lista_produtos')
    else:
        form = ProdutoForm(instance=produto, user=request.user)
    return render(request, 'estoque/form_produto.html', {'form': form, 'titulo': 'Editar Item'})

@login_required
def registrar_movimentacao(request):
    if request.method == 'POST':
        form = MovimentacaoForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    m = form.save(commit=False)
                    m.empresa = request.user.empresa
                    m.save()
                    if m.tipo == 'E' and m.fornecedor:
                        plano, _ = PlanoDeContas.objects.get_or_create(empresa=request.user.empresa, nome="COMPRA DE MERCADORIAS", tipo='D', defaults={'codigo': '2.01'})
                        total_compra = m.quantidade * m.valor_unitario
                        if m.forma_pagamento == 'V':
                            caixa = form.cleaned_data.get('caixa_pagamento')
                            if caixa:
                                Lancamento.objects.create(empresa=request.user.empresa, caixa=caixa, plano_de_contas=plano, data_lancamento=m.data.date(), descricao=f"Compra: {m.quantidade}x {m.produto.nome}", valor=total_compra, tipo='D')
                        else:
                            qtd_parcelas = m.num_parcelas or 1
                            valor_parcela = total_compra / qtd_parcelas
                            for i in range(qtd_parcelas):
                                Conta.objects.create(empresa=request.user.empresa, descricao=f"Parc {i+1}/{qtd_parcelas} - {m.produto.nome}", plano_de_contas=plano, cadastro=m.fornecedor, valor=valor_parcela, data_vencimento=m.data.date() + timedelta(days=30 * (i + 1)), status='PENDENTE', documento=f"MOV-{m.id}")
                messages.success(request, "Estoque e Financeiro atualizados!")
                return redirect('estoque:lista_produtos')
            except Exception as e:
                messages.error(request, f"Erro: {str(e)}")
    else:
        form = MovimentacaoForm(user=request.user)
    return render(request, 'estoque/form_movimentacao.html', {'form': form})

@login_required
def buscar_produtos(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2: return JsonResponse([], safe=False)
    produtos = Produto.objects.filter(empresa=request.user.empresa).filter(Q(nome__icontains=q) | Q(descricao__icontains=q)).order_by('nome')[:20]
    data = [{'id': p.id, 'nome': p.nome, 'estoque': p.estoque_deposito, 'preco': str(p.preco_venda)} for p in produtos]
    return JsonResponse(data, safe=False)

@login_required
def rel_produtos_pdf(request):
    from core.pdf import pdf_response, nome_arquivo
    produtos = Produto.objects.filter(empresa=request.user.empresa).select_related('categoria').order_by('categoria__ordem', 'nome')
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    categoria_id = request.GET.get('categoria', '')
    if q:
        produtos = produtos.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
    if tipo:
        produtos = produtos.filter(tipo=tipo)
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    filtros = []
    if q:
        filtros.append(f"Busca: {q}")
    if tipo:
        filtros.append(f"Tipo: {'Produto' if tipo == 'P' else 'Serviço'}")
    if categoria_id:
        cat = Categoria.objects.filter(id=categoria_id, empresa=request.user.empresa).first()
        if cat:
            filtros.append(f"Categoria: {cat.nome}")
    return pdf_response(request, 'estoque/rel_produtos_pdf.html', {
        'produtos': produtos,
        'rel_titulo': 'Relatório de Produtos / Estoque',
        'rel_filtros': ' | '.join(filtros) if filtros else 'Sem filtros',
    }, nome_arquivo('relatorio-produtos'))


@login_required
def rel_movimentacoes_pdf(request):
    from core.pdf import pdf_response, nome_arquivo
    queryset = MovimentacaoEstoque.objects.filter(
        empresa=request.user.empresa
    ).select_related('produto', 'fornecedor').order_by('-data')
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if q:
        queryset = queryset.filter(Q(produto__nome__icontains=q) | Q(fornecedor__nome__icontains=q))
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    from core.datas import filtrar_periodo
    queryset = filtrar_periodo(queryset, 'data', data_inicio, data_fim)
    total_entradas = sum((m.quantidade * m.valor_unitario for m in queryset if m.tipo == 'E'), 0)
    total_saidas = sum((m.quantidade * m.valor_unitario for m in queryset if m.tipo == 'S'), 0)
    filtros = []
    if q:
        filtros.append(f"Busca: {q}")
    if tipo:
        filtros.append(f"Tipo: {'Entrada' if tipo == 'E' else 'Saída'}")
    if data_inicio:
        filtros.append(f"De: {data_inicio}")
    if data_fim:
        filtros.append(f"Até: {data_fim}")
    return pdf_response(request, 'estoque/rel_mov_pdf.html', {
        'movimentacoes': queryset,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'rel_titulo': 'Relatório de Movimentações de Estoque',
        'rel_filtros': ' | '.join(filtros) if filtros else 'Sem filtros',
        'page_size': 'A4 landscape',
    }, nome_arquivo('relatorio-movimentacoes'))


@login_required
def historico_movimentacoes(request):
    queryset = MovimentacaoEstoque.objects.filter(
        empresa=request.user.empresa
    ).select_related('produto', 'fornecedor').order_by('-data')

    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    if q:
        queryset = queryset.filter(
            Q(produto__nome__icontains=q) | Q(fornecedor__nome__icontains=q)
        )
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    from core.datas import filtrar_periodo
    queryset = filtrar_periodo(queryset, 'data', data_inicio, data_fim)

    return render(request, 'estoque/historico_movimentacoes.html', {
        'movimentacoes': queryset,
        'q': q,
        'tipo': tipo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.filter(empresa=request.user.empresa).order_by('ordem', 'nome')
    return render(request, 'estoque/lista_categorias.html', {'categorias': categorias})

@login_required
def nova_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.empresa = request.user.empresa
            cat.save()
            messages.success(request, f"Categoria '{cat.nome}' criada!")
            return redirect('estoque:lista_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'estoque/form_categoria.html', {'form': form, 'titulo': 'Nova Categoria'})

@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria atualizada!")
            return redirect('estoque:lista_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'estoque/form_categoria.html', {'form': form, 'titulo': 'Editar Categoria'})

@login_required
def excluir_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, "Categoria excluída!")
    return redirect('estoque:lista_categorias')
