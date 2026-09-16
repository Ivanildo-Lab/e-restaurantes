from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from .models import Produto, MovimentacaoEstoque
from .forms import ProdutoForm, MovimentacaoForm
from datetime import timedelta
from financeiro.models import Conta, Lancamento, PlanoDeContas

@login_required
def lista_produtos(request):
    tipo_filtro = request.GET.get('tipo')
    produtos = Produto.objects.filter(empresa=request.user.empresa).order_by('nome')
    if tipo_filtro: produtos = produtos.filter(tipo=tipo_filtro)
    return render(request, 'estoque/lista_produtos.html', {'produtos': produtos, 'filtro': tipo_filtro})

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
        form = ProdutoForm()
    return render(request, 'estoque/form_produto.html', {'form': form, 'titulo': 'Novo Item'})

@login_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, "Item atualizado!")
            return redirect('estoque:lista_produtos')
    else:
        form = ProdutoForm(instance=produto)
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
