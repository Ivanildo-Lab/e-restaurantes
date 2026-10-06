from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from .models import Venda, ItemVenda
from .forms import ItemVendaForm
from financeiro.models import Conta, Lancamento, PlanoDeContas, Caixa, FormaPagamento
from core.models import ParametroSistema


@login_required
def nova_venda(request):
    if request.method == 'POST':
        cliente = (request.POST.get('cliente') or '').strip() or 'Consumidor Final'
        venda = Venda.objects.create(empresa=request.user.empresa, cliente=cliente)
        messages.success(request, f"Venda #{venda.id} iniciada!")
        return redirect('pdv:venda_aberta', venda_id=venda.id)
    return render(request, 'pdv/nova_venda.html')


@login_required
def venda_aberta(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id, empresa=request.user.empresa, status='ABERTA')
    itens = venda.itens.select_related('produto').order_by('-id')
    form = ItemVendaForm(user=request.user)
    total = venda.total_atual()
    formas = FormaPagamento.objects.filter(empresa=request.user.empresa, ativo=True, tipo='V')
    caixas = Caixa.objects.filter(empresa=request.user.empresa)
    return render(request, 'pdv/venda.html', {
        'venda': venda, 'itens': itens, 'form': form, 'total': total,
        'formas_pagamento': formas, 'caixas': caixas,
    })


@login_required
def adicionar_item(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id, empresa=request.user.empresa, status='ABERTA')
    if request.method == 'POST':
        form = ItemVendaForm(request.POST, user=request.user)
        if form.is_valid():
            produto = form.cleaned_data['produto']
            quantidade = form.cleaned_data['quantidade']
            if produto.tipo == 'P' and produto.estoque_deposito < quantidade:
                messages.error(request, f"Estoque insuficiente de '{produto.nome}'. Disponível: {produto.estoque_deposito}")
                return redirect('pdv:venda_aberta', venda_id=venda.id)
            item = form.save(commit=False)
            item.empresa = request.user.empresa
            item.venda = venda
            item.valor_unitario = produto.preco_venda
            item.save()
            messages.success(request, f"{quantidade}x {produto.nome} adicionado!")
    return redirect('pdv:venda_aberta', venda_id=venda.id)


@login_required
def remover_item(request, item_id):
    item = get_object_or_404(ItemVenda, id=item_id, empresa=request.user.empresa, venda__status='ABERTA')
    venda_id = item.venda_id
    item.delete()
    messages.success(request, "Item removido!")
    return redirect('pdv:venda_aberta', venda_id=venda_id)


@login_required
def cancelar_venda(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id, empresa=request.user.empresa, status='ABERTA')
    venda.delete()
    messages.success(request, f"Venda #{venda_id} cancelada!")
    return redirect('pdv:nova_venda')


@login_required
def finalizar_venda(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id, empresa=request.user.empresa, status='ABERTA')
    if request.method != 'POST' or request.POST.get('processar') != '1':
        return redirect('pdv:venda_aberta', venda_id=venda.id)
    if venda.total_itens() == 0:
        messages.error(request, "Venda sem itens — adicione produtos ou cancele a venda.")
        return redirect('pdv:venda_aberta', venda_id=venda.id)
    imprimir = request.POST.get('imprimir', 'sim')
    try:
        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            total = venda.total_atual()
            forma_id = request.POST.get('forma_id')
            forma = FormaPagamento.objects.filter(id=forma_id, empresa=request.user.empresa, ativo=True).first()
            if forma is None:
                forma = FormaPagamento.objects.filter(empresa=request.user.empresa, ativo=True, nome__iexact='DINHEIRO').first()
            if forma is None:
                forma, _ = FormaPagamento.objects.get_or_create(
                    empresa=request.user.empresa, nome='DINHEIRO', defaults={'tipo': 'V', 'ativo': True}
                )
            if forma.tipo != 'V':
                messages.error(request, "PDV aceita somente pagamento à vista.")
                return redirect('pdv:venda_aberta', venda_id=venda.id)
            try:
                recebido = Decimal(str(request.POST.get('valor_recebido') or '0').replace(',', '.'))
            except Exception:
                recebido = Decimal('0')
            if recebido < 0:
                recebido = Decimal('0')
            if recebido and recebido < total:
                messages.error(request, f"Valor recebido (R$ {recebido}) menor que o total (R$ {total}).")
                return redirect('pdv:venda_aberta', venda_id=venda.id)
            troco = recebido - total if recebido > total else Decimal('0')

            # Baixa de estoque com revalidacao
            for item in venda.itens.select_related('produto'):
                prod = item.produto
                if prod.tipo == 'P':
                    prod.refresh_from_db()
                    if prod.estoque_deposito < item.quantidade:
                        raise ValueError(f"Estoque insuficiente de '{prod.nome}'. Disponível: {prod.estoque_deposito}")
                    prod.estoque_deposito -= item.quantidade
                    prod.save()

            plano_r, _ = PlanoDeContas.objects.get_or_create(
                empresa=request.user.empresa, nome="RECEITA DE PDV",
                tipo='R', defaults={'codigo': '1.02'}
            )
            caixa_id = request.POST.get('caixa_id')
            caixa_sel = Caixa.objects.filter(id=caixa_id, empresa=request.user.empresa).first()
            if not caixa_sel:
                param = ParametroSistema.objects.filter(empresa=request.user.empresa, chave='CAIXA_PADRAO_ID').first()
                if param:
                    caixa_sel = Caixa.objects.filter(id=param.valor, empresa=request.user.empresa).first()

            documento = venda.documento_financeiro
            agora = timezone.now()
            ct = Conta.objects.create(
                empresa=request.user.empresa, descricao=f"PDV {forma.nome} Venda-#{venda.id}",
                plano_de_contas=plano_r, cadastro=None, valor=total,
                data_vencimento=agora.date(), status='PAGA', documento=documento
            )
            if caixa_sel:
                Lancamento.objects.create(
                    empresa=request.user.empresa, caixa=caixa_sel, plano_de_contas=plano_r,
                    conta_origem=ct, data_lancamento=agora.date(), valor=total,
                    tipo='C', descricao=f"Receb. {forma.nome} Venda-#{venda.id}"
                )

            venda.valor_total = total
            venda.valor_recebido = recebido
            venda.troco = troco
            venda.forma_pagamento = forma
            venda.caixa = caixa_sel
            venda.data_finalizacao = agora
            venda.status = 'FINALIZADA'
            venda.save()

        messages.success(request, f"Venda #{venda.id} finalizada! ({forma.nome})")
        if imprimir == 'nao':
            return redirect('pdv:nova_venda')
        return redirect('pdv:recibo_venda', venda_id=venda.id)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('pdv:venda_aberta', venda_id=venda.id)
    except Exception as e:
        messages.error(request, f"Erro ao finalizar venda: {str(e)}")
        return redirect('pdv:venda_aberta', venda_id=venda.id)


@login_required
def recibo_venda(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id, empresa=request.user.empresa)
    itens = venda.itens.select_related('produto').order_by('id')
    pagamento = Conta.objects.filter(empresa=request.user.empresa, documento=venda.documento_financeiro).first()
    return render(request, 'pdv/recibo.html', {
        'venda': venda, 'itens': itens, 'pagamento': pagamento, 'empresa': request.user.empresa
    })


@login_required
def historico_vendas(request):
    queryset = Venda.objects.filter(
        empresa=request.user.empresa, status='FINALIZADA'
    ).select_related('forma_pagamento').order_by('-data_finalizacao')

    q = request.GET.get('q', '').strip()
    forma_id = request.GET.get('forma', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    if q:
        queryset = queryset.filter(Q(cliente__icontains=q) | Q(id__icontains=q))
    if forma_id:
        queryset = queryset.filter(forma_pagamento_id=forma_id)
    from core.datas import filtrar_periodo
    queryset = filtrar_periodo(queryset, 'data_finalizacao', data_inicio, data_fim)

    formas = FormaPagamento.objects.filter(empresa=request.user.empresa, ativo=True)
    return render(request, 'pdv/historico.html', {
        'vendas': queryset, 'formas': formas,
        'q': q, 'forma_id': forma_id, 'data_inicio': data_inicio, 'data_fim': data_fim,
    })


@login_required
def rel_vendas_pdf(request):
    from core.pdf import pdf_response, nome_arquivo
    queryset = Venda.objects.filter(
        empresa=request.user.empresa, status='FINALIZADA'
    ).select_related('forma_pagamento').order_by('-data_finalizacao')
    q = request.GET.get('q', '').strip()
    forma_id = request.GET.get('forma', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if q:
        queryset = queryset.filter(Q(cliente__icontains=q) | Q(id__icontains=q))
    if forma_id:
        queryset = queryset.filter(forma_pagamento_id=forma_id)
    from core.datas import filtrar_periodo
    queryset = filtrar_periodo(queryset, 'data_finalizacao', data_inicio, data_fim)
    soma_total = sum((v.valor_total for v in queryset), 0)
    filtros = []
    if q:
        filtros.append(f"Busca: {q}")
    if forma_id:
        f = FormaPagamento.objects.filter(id=forma_id, empresa=request.user.empresa).first()
        if f:
            filtros.append(f"Pagamento: {f.nome}")
    if data_inicio:
        filtros.append(f"De: {data_inicio}")
    if data_fim:
        filtros.append(f"Até: {data_fim}")
    return pdf_response(request, 'pdv/rel_vendas_pdf.html', {
        'vendas': queryset,
        'soma_total': soma_total,
        'rel_titulo': 'Relatório de Vendas PDV',
        'rel_filtros': ' | '.join(filtros) if filtros else 'Sem filtros',
    }, nome_arquivo('relatorio-vendas-pdv'))
