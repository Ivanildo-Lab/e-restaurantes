from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from .models import Mesa, ItemMesa
from .forms import MesaForm, ItemMesaForm
from estoque.models import Produto
from financeiro.models import Conta, Lancamento, PlanoDeContas, Caixa, FormaPagamento
from core.models import ParametroSistema

def home(request):
    return render(request, 'home.html')

@login_required
def mapa_mesas(request):
    mesas = Mesa.objects.filter(empresa=request.user.empresa).order_by('numero')
    produtos = Produto.objects.filter(empresa=request.user.empresa).order_by('nome')
    caixas = Caixa.objects.filter(empresa=request.user.empresa)
    formas_pagamento = FormaPagamento.objects.filter(empresa=request.user.empresa, ativo=True)
    return render(request, 'restaurantes/mapa_mesas.html', {
        'mesas': mesas, 'produtos': produtos, 'caixas': caixas, 'formas_pagamento': formas_pagamento
    })

@login_required
def abrir_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa)
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            mesa.responsavel = form.cleaned_data.get('responsavel') or 'Consumidor Final'
            mesa.status = 'OCUPADA'
            mesa.data_abertura = timezone.now()
            mesa.data_fechamento = None
            mesa.valor_total = 0
            mesa.save()
            messages.success(request, f"Mesa {mesa.numero} aberta!")
            return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)
    else:
        form = MesaForm(initial={'responsavel': 'Consumidor Final'})
    return render(request, 'restaurantes/abrir_mesa.html', {'mesa': mesa, 'form': form})

@login_required
def mesa_aberta(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa, status='OCUPADA')
    itens = mesa.itemmesa_set.select_related('produto').order_by('-id')
    form = ItemMesaForm(user=request.user)
    total = mesa.total_atual()
    return render(request, 'restaurantes/mesa_aberta.html', {'mesa': mesa, 'itens': itens, 'form': form, 'total': total})

@login_required
def adicionar_item(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa, status='OCUPADA')
    if request.method == 'POST':
        form = ItemMesaForm(request.POST, user=request.user)
        if form.is_valid():
            produto = form.cleaned_data['produto']
            quantidade = form.cleaned_data['quantidade']
            if produto.tipo == 'P' and produto.estoque_deposito < quantidade:
                messages.error(request, f"Estoque insuficiente de '{produto.nome}'. Disponível: {produto.estoque_deposito}")
                return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)
            item = form.save(commit=False)
            item.empresa = request.user.empresa
            item.mesa = mesa
            item.valor_unitario = produto.preco_venda
            item.save()
            if produto.tipo == 'P':
                produto.estoque_deposito -= quantidade
                produto.save()
            messages.success(request, f"{quantidade}x {produto.nome} adicionado!")
    return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)

@login_required
def remover_item(request, item_id):
    item = get_object_or_404(ItemMesa, id=item_id, empresa=request.user.empresa)
    mesa = item.mesa
    if item.produto.tipo == 'P':
        item.produto.estoque_deposito += item.quantidade
        item.produto.save()
    item.delete()
    messages.success(request, "Item removido!")
    return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)

@login_required
def fechar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa, status='OCUPADA')
    itens = mesa.itemmesa_set.select_related('produto').order_by('id')
    total = mesa.total_atual()
    imprimir = request.POST.get('imprimir', 'sim')

    if request.method == 'POST' and request.POST.get('processar_fechamento') == '1':
        try:
            from django.db import transaction as db_transaction
            with db_transaction.atomic():
                plano_r, _ = PlanoDeContas.objects.get_or_create(
                    empresa=request.user.empresa, nome="RECEITA DE RESTAURANTE",
                    tipo='R', defaults={'codigo': '1.01'}
                )

                caixa_id = request.POST.get('caixa_id')
                caixa_sel = Caixa.objects.filter(id=caixa_id, empresa=request.user.empresa).first()
                if not caixa_sel:
                    param = ParametroSistema.objects.filter(empresa=request.user.empresa, chave='CAIXA_PADRAO_ID').first()
                    if param: caixa_sel = Caixa.objects.filter(id=param.valor, empresa=request.user.empresa).first()

                pgto_ids = request.POST.getlist('pgto_ids[]')
                pgto_valores = request.POST.getlist('pgto_valores[]')
                pgto_parcelas = request.POST.getlist('pgto_parcelas[]')

                for f_id, f_val_str, f_parc_str in zip(pgto_ids, pgto_valores, pgto_parcelas):
                    from financeiro.models import FormaPagamento
                    forma = get_object_or_404(FormaPagamento, id=f_id, empresa=request.user.empresa)
                    v_fatia = Decimal(f_val_str)
                    n_parc = int(f_parc_str) if f_parc_str else 1

                    if forma.tipo == 'V':
                        ct = Conta.objects.create(
                            empresa=request.user.empresa, descricao=f"Pgto {forma.nome} Mesa-{mesa.numero}",
                            plano_de_contas=plano_r, cadastro=None, valor=v_fatia,
                            data_vencimento=timezone.now().date(), status='PAGA', documento=f"MESA-{mesa.id}"
                        )
                        if caixa_sel:
                            Lancamento.objects.create(
                                empresa=request.user.empresa, caixa=caixa_sel, plano_de_contas=plano_r,
                                conta_origem=ct, data_lancamento=timezone.now().date(), valor=v_fatia,
                                tipo='C', descricao=f"Receb. {forma.nome} Mesa-{mesa.numero}"
                            )
                    else:
                        v_parc = v_fatia / Decimal(n_parc)
                        for i in range(n_parc):
                            Conta.objects.create(
                                empresa=request.user.empresa,
                                descricao=f"Parc {i+1}/{n_parc} {forma.nome} Mesa-{mesa.numero}",
                                plano_de_contas=plano_r, cadastro=None, valor=v_parc,
                                data_vencimento=timezone.now().date() + __import__('datetime').timedelta(days=30*i),
                                status='PENDENTE', documento=f"MESA-{mesa.id}"
                            )

                mesa.valor_total = total
                mesa.data_fechamento = timezone.now()
                mesa.status = 'LIVRE'
                mesa.save()

            messages.success(request, "Mesa fechada com sucesso!")
            if imprimir == 'nao':
                return redirect('restaurantes:mapa_mesas')
            return redirect('restaurantes:comprovante_mesa', mesa_id=mesa.id)
        except Exception as e:
            messages.error(request, f"Erro ao fechar mesa: {str(e)}")
            return redirect('restaurantes:mapa_mesas')

    return render(request, 'restaurantes/fechar_mesa.html', {'mesa': mesa, 'itens': itens, 'total': total})

@login_required
def comprovante_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa)
    itens = mesa.itemmesa_set.select_related('produto').order_by('id')
    pagamentos = Conta.objects.filter(empresa=request.user.empresa, documento=f"MESA-{mesa.id}")
    return render(request, 'restaurantes/comprovante.html', {
        'mesa': mesa, 'itens': itens, 'pagamentos': pagamentos, 'empresa': request.user.empresa
    })

@login_required
def gerenciar_mesas(request):
    mesas = Mesa.objects.filter(empresa=request.user.empresa).order_by('numero')
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            mesa = form.save(commit=False)
            mesa.empresa = request.user.empresa
            mesa.save()
            messages.success(request, f"Mesa {mesa.numero} criada!")
            return redirect('restaurantes:gerenciar_mesas')
    else:
        form = MesaForm()
    return render(request, 'restaurantes/gerenciar_mesas.html', {'mesas': mesas, 'form': form})

@login_required
def editar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa)
    if request.method == 'POST':
        form = MesaForm(request.POST, instance=mesa)
        if form.is_valid():
            form.save()
            messages.success(request, "Mesa atualizada!")
            return redirect('restaurantes:gerenciar_mesas')
    else:
        form = MesaForm(instance=mesa)
    return render(request, 'restaurantes/gerenciar_mesas.html', {'mesas': Mesa.objects.filter(empresa=request.user.empresa).order_by('numero'), 'form': form, 'editando': mesa})

@login_required
def excluir_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa)
    if mesa.status == 'OCUPADA':
        messages.error(request, "Não é possível excluir uma mesa ocupada!")
    else:
        mesa.delete()
        messages.success(request, "Mesa excluída!")
    return redirect('restaurantes:gerenciar_mesas')
