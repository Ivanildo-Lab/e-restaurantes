from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from .models import Mesa, ItemMesa, MesaOcupacao
from .forms import MesaForm, ItemMesaForm


def _ocupacao_aberta(mesa, empresa):
    return MesaOcupacao.objects.filter(
        mesa=mesa, empresa=empresa, status='ABERTA'
    ).order_by('-data_abertura').first()
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
    if mesa.status == 'OCUPADA':
        messages.info(request, f"Mesa {mesa.numero} já está ocupada.")
        return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['numero'] = mesa.numero
        form = MesaForm(post_data)
        if form.is_valid():
            responsavel = form.cleaned_data.get('responsavel') or 'Consumidor Final'
            agora = timezone.now()
            # Limpa orfaos legados sem ocupacao (nao auditaveis) para nao poluir
            mesa.itemmesa_set.filter(ocupacao__isnull=True).delete()
            ocupacao = MesaOcupacao.objects.create(
                empresa=request.user.empresa,
                mesa=mesa,
                responsavel=responsavel,
                data_abertura=agora,
                status='ABERTA',
            )
            mesa.responsavel = responsavel
            mesa.status = 'OCUPADA'
            mesa.data_abertura = agora
            mesa.data_fechamento = None
            mesa.valor_total = 0
            mesa.save()
            messages.success(request, f"Mesa {mesa.numero} aberta! (Sessão #{ocupacao.id})")
            return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)
    else:
        form = MesaForm(initial={'responsavel': 'Consumidor Final'})
    return render(request, 'restaurantes/abrir_mesa.html', {'mesa': mesa, 'form': form})

@login_required
def mesa_aberta(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa, status='OCUPADA')
    ocupacao = _ocupacao_aberta(mesa, request.user.empresa)
    if ocupacao is None:
        # Auto-reparo de ocupacao aberta legada (anterior ao modelo de sessoes)
        ocupacao = MesaOcupacao.objects.create(
            empresa=request.user.empresa,
            mesa=mesa,
            responsavel=mesa.responsavel or 'Consumidor Final',
            data_abertura=mesa.data_abertura or timezone.now(),
            status='ABERTA',
        )
        mesa.itemmesa_set.filter(ocupacao__isnull=True).update(ocupacao=ocupacao)
    itens = ocupacao.itens.select_related('produto').order_by('-id')
    form = ItemMesaForm(user=request.user)
    total = ocupacao.total_atual()
    return render(request, 'restaurantes/mesa_aberta.html', {'mesa': mesa, 'ocupacao': ocupacao, 'itens': itens, 'form': form, 'total': total})

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
            ocupacao = _ocupacao_aberta(mesa, request.user.empresa)
            if ocupacao is None:
                messages.error(request, "Sessão da mesa não encontrada. Reabra a mesa.")
                return redirect('restaurantes:mapa_mesas')
            item = form.save(commit=False)
            item.empresa = request.user.empresa
            item.mesa = mesa
            item.ocupacao = ocupacao
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
    if item.ocupacao is not None and item.ocupacao.status != 'ABERTA':
        messages.error(request, "Não é possível remover item de uma sessão já fechada (auditoria).")
        return redirect('restaurantes:mapa_mesas')
    if item.produto.tipo == 'P':
        item.produto.estoque_deposito += item.quantidade
        item.produto.save()
    item.delete()
    messages.success(request, "Item removido!")
    return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)

@login_required
def cancelar_abertura(request, mesa_id):
    """Desistencia sem consumo: libera a mesa sem gerar sessao no historico/auditoria."""
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa, status='OCUPADA')
    ocupacao = _ocupacao_aberta(mesa, request.user.empresa)
    if ocupacao is None:
        mesa.status = 'LIVRE'
        mesa.responsavel = 'Consumidor Final'
        mesa.data_abertura = None
        mesa.data_fechamento = None
        mesa.valor_total = 0
        mesa.save()
        mesa.itemmesa_set.filter(ocupacao__isnull=True).delete()
        messages.success(request, f"Mesa {mesa.numero} liberada!")
        return redirect('restaurantes:mapa_mesas')
    if ocupacao.total_itens() > 0:
        messages.error(request, "Mesa possui itens — remova os itens ou feche a mesa normalmente.")
        return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)
    numero = mesa.numero
    ocupacao.delete()
    mesa.itemmesa_set.filter(ocupacao__isnull=True).delete()
    mesa.status = 'LIVRE'
    mesa.responsavel = 'Consumidor Final'
    mesa.data_abertura = None
    mesa.data_fechamento = None
    mesa.valor_total = 0
    mesa.save()
    messages.success(request, f"Mesa {numero} liberada (sem consumo)!")
    return redirect('restaurantes:mapa_mesas')


@login_required
def fechar_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa, status='OCUPADA')
    ocupacao = _ocupacao_aberta(mesa, request.user.empresa)
    if ocupacao is None:
        messages.error(request, "Sessão da mesa não encontrada. Reabra a mesa.")
        return redirect('restaurantes:mapa_mesas')
    itens = ocupacao.itens.select_related('produto').order_by('id')
    total = ocupacao.total_atual()
    imprimir = request.POST.get('imprimir', 'sim')

    if request.method == 'POST' and request.POST.get('processar_fechamento') == '1':
        if ocupacao.total_itens() == 0:
            messages.error(request, "Mesa sem consumo — use LIBERAR MESA em vez de fechar.")
            return redirect('restaurantes:mesa_aberta', mesa_id=mesa.id)
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

                # Padrao: sem forma selecionada => DINHEIRO a vista no valor total
                pagamento_padrao = False
                if not pgto_ids:
                    forma_din = FormaPagamento.objects.filter(
                        empresa=request.user.empresa, ativo=True, nome__iexact='DINHEIRO'
                    ).first()
                    if forma_din is None:
                        forma_din = FormaPagamento.objects.filter(
                            empresa=request.user.empresa, ativo=True, nome__icontains='DINHEIRO'
                        ).first()
                    if forma_din is None:
                        forma_din, _ = FormaPagamento.objects.get_or_create(
                            empresa=request.user.empresa, nome='DINHEIRO',
                            defaults={'tipo': 'V', 'ativo': True}
                        )
                    pgto_ids = [str(forma_din.id)]
                    pgto_valores = [str(total)]
                    pgto_parcelas = ['1']
                    pagamento_padrao = True

                documento = ocupacao.documento_financeiro
                agora = timezone.now()

                try:
                    recebido = Decimal(str(request.POST.get('valor_recebido') or '0').replace(',', '.'))
                except Exception:
                    recebido = Decimal('0')
                if recebido < 0:
                    recebido = Decimal('0')
                troco = recebido - total if recebido > total else Decimal('0')

                for f_id, f_val_str, f_parc_str in zip(pgto_ids, pgto_valores, pgto_parcelas):
                    forma = get_object_or_404(FormaPagamento, id=f_id, empresa=request.user.empresa)
                    v_fatia = Decimal(f_val_str)
                    n_parc = int(f_parc_str) if f_parc_str else 1

                    if forma.tipo == 'V':
                        ct = Conta.objects.create(
                            empresa=request.user.empresa, descricao=f"Pgto {forma.nome} Mesa-{mesa.numero} Ocup-{ocupacao.id}",
                            plano_de_contas=plano_r, cadastro=None, valor=v_fatia,
                            data_vencimento=agora.date(), status='PAGA', documento=documento
                        )
                        if caixa_sel:
                            Lancamento.objects.create(
                                empresa=request.user.empresa, caixa=caixa_sel, plano_de_contas=plano_r,
                                conta_origem=ct, data_lancamento=agora.date(), valor=v_fatia,
                                tipo='C', descricao=f"Receb. {forma.nome} Mesa-{mesa.numero} Ocup-{ocupacao.id}"
                            )
                    else:
                        v_parc = v_fatia / Decimal(n_parc)
                        for i in range(n_parc):
                            Conta.objects.create(
                                empresa=request.user.empresa,
                                descricao=f"Parc {i+1}/{n_parc} {forma.nome} Mesa-{mesa.numero} Ocup-{ocupacao.id}",
                                plano_de_contas=plano_r, cadastro=None, valor=v_parc,
                                data_vencimento=agora.date() + __import__('datetime').timedelta(days=30*i),
                                status='PENDENTE', documento=documento
                            )

                ocupacao.valor_total = total
                ocupacao.valor_recebido = recebido
                ocupacao.troco = troco
                ocupacao.data_fechamento = agora
                ocupacao.status = 'FECHADA'
                ocupacao.save()

                mesa.valor_total = total
                mesa.data_fechamento = agora
                mesa.status = 'LIVRE'
                mesa.save()

            if pagamento_padrao:
                messages.success(request, f"Mesa fechada com sucesso! (Sessão #{ocupacao.id}) Pagamento padrão: DINHEIRO.")
            else:
                messages.success(request, f"Mesa fechada com sucesso! (Sessão #{ocupacao.id})")
            if imprimir == 'nao':
                return redirect('restaurantes:mapa_mesas')
            return redirect('restaurantes:comprovante_mesa', ocupacao_id=ocupacao.id)
        except Exception as e:
            messages.error(request, f"Erro ao fechar mesa: {str(e)}")
            return redirect('restaurantes:mapa_mesas')

    return render(request, 'restaurantes/fechar_mesa.html', {
        'mesa': mesa, 'ocupacao': ocupacao, 'itens': itens, 'total': total,
        'caixas': Caixa.objects.filter(empresa=request.user.empresa),
        'formas_pagamento': FormaPagamento.objects.filter(empresa=request.user.empresa, ativo=True),
    })

def _rotulo_pagamento(descricao):
    """Descricao tecnica -> rotulo curto p/ comprovante. Ex: 'Pgto DINHEIRO Mesa-MESA 01 Ocup-17' -> 'DINHEIRO'."""
    import re
    d = (descricao or '').strip()
    m = re.match(r'^Parc\s+(\d+/\d+)\s+(.+?)(?:\s+Mesa-.*)?$', d)
    if m:
        return f"{m.group(2).strip()} {m.group(1)} (A PRAZO)"
    m = re.match(r'^(?:Pgto|Receb\.)\s+(.+?)(?:\s+Mesa-.*)?$', d)
    if m:
        return m.group(1).strip()
    return d


@login_required
def comprovante_mesa(request, ocupacao_id):
    ocupacao = get_object_or_404(MesaOcupacao, id=ocupacao_id, empresa=request.user.empresa)
    mesa = ocupacao.mesa
    itens = ocupacao.itens.select_related('produto').order_by('id')
    # Somente pagamentos DESTA sessao. Fallback legado: sessoes migradas cujo
    # financeiro foi lancado como MESA-{id} antes das sessoes existirem.
    pagamentos = Conta.objects.filter(
        empresa=request.user.empresa,
        documento=ocupacao.documento_financeiro,
    ).order_by('id')
    if not pagamentos.exists() and ocupacao.data_fechamento:
        from core.datas import filtrar_periodo
        dia = timezone.localtime(ocupacao.data_fechamento).date().isoformat()
        pagamentos = filtrar_periodo(
            Conta.objects.filter(empresa=request.user.empresa, documento=f"MESA-{mesa.id}"),
            'criado_em', dia, dia,
        ).order_by('id')
    total_pago = Decimal('0')
    total_prazo = Decimal('0')
    for pg in pagamentos:
        pg.rotulo = _rotulo_pagamento(pg.descricao)
        if pg.status == 'PAGA':
            total_pago += pg.valor
        else:
            total_prazo += pg.valor
    return render(request, 'restaurantes/comprovante.html', {
        'mesa': mesa, 'ocupacao': ocupacao, 'itens': itens,
        'pagamentos': pagamentos, 'empresa': request.user.empresa,
        'total_pago': total_pago, 'total_prazo': total_prazo,
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
    from django.db.models.deletion import ProtectedError
    mesa = get_object_or_404(Mesa, id=mesa_id, empresa=request.user.empresa)
    if mesa.status == 'OCUPADA':
        messages.error(request, "Não é possível excluir uma mesa ocupada!")
    else:
        try:
            mesa.delete()
            messages.success(request, "Mesa excluída!")
        except ProtectedError:
            messages.error(request, "Não é possível excluir: esta mesa possui histórico de ocupações (auditoria).")
    return redirect('restaurantes:gerenciar_mesas')

@login_required
def historico_mesas(request):
    queryset = MesaOcupacao.objects.filter(
        empresa=request.user.empresa,
        status='FECHADA',
    ).select_related('mesa').order_by('-data_fechamento')

    q = request.GET.get('q', '').strip()
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    if q:
        queryset = queryset.filter(
            Q(mesa__numero__icontains=q) | Q(responsavel__icontains=q)
        )
    from core.datas import filtrar_periodo
    queryset = filtrar_periodo(queryset, 'data_fechamento', data_inicio, data_fim)

    return render(request, 'restaurantes/historico_mesas.html', {
        'ocupacoes': queryset,
        'q': q,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })


@login_required
def rel_historico_pdf(request):
    from core.pdf import pdf_response, nome_arquivo
    queryset = MesaOcupacao.objects.filter(
        empresa=request.user.empresa,
        status='FECHADA',
    ).select_related('mesa').order_by('-data_fechamento')
    q = request.GET.get('q', '').strip()
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if q:
        queryset = queryset.filter(Q(mesa__numero__icontains=q) | Q(responsavel__icontains=q))
    from core.datas import filtrar_periodo
    queryset = filtrar_periodo(queryset, 'data_fechamento', data_inicio, data_fim)
    soma_total = sum((oc.valor_total for oc in queryset), 0)
    filtros = []
    if q:
        filtros.append(f"Busca: {q}")
    if data_inicio:
        filtros.append(f"De: {data_inicio}")
    if data_fim:
        filtros.append(f"Até: {data_fim}")
    return pdf_response(request, 'restaurantes/rel_historico_pdf.html', {
        'ocupacoes': queryset,
        'soma_total': soma_total,
        'rel_titulo': 'Relatório de Histórico de Mesas',
        'rel_filtros': ' | '.join(filtros) if filtros else 'Sem filtros',
    }, nome_arquivo('relatorio-historico-mesas'))
