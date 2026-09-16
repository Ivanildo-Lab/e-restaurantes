from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import date
from .models import Conta, FormaPagamento, Lancamento, Caixa, PlanoDeContas
from .forms import ContaForm, FormaPagamentoForm, LancamentoManualForm, CaixaForm, PlanoContasForm
from core.models import ParametroSistema
from decimal import Decimal
import calendar
import random

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

@login_required
def lista_caixas(request):
    caixas = Caixa.objects.filter(empresa=request.user.empresa)
    caixa_padrao = ParametroSistema.objects.filter(empresa=request.user.empresa, chave='CAIXA_PADRAO_ID').first()
    return render(request, 'financeiro/caixa_list.html', {'caixas': caixas, 'caixa_padrao_id': caixa_padrao.valor if caixa_padrao else None})

@login_required
def adicionar_caixa(request):
    if request.method == 'POST':
        form = CaixaForm(request.POST)
        if form.is_valid():
            caixa = form.save(commit=False)
            caixa.empresa = request.user.empresa
            caixa.save()
            messages.success(request, "Caixa adicionado!")
            return redirect('financeiro:lista_caixas')
    else:
        form = CaixaForm()
    return render(request, 'financeiro/caixa_form.html', {'form': form})

@login_required
def editar_caixa(request, id):
    caixa = get_object_or_404(Caixa, id=id, empresa=request.user.empresa)
    if request.method == 'POST':
        form = CaixaForm(request.POST, instance=caixa)
        if form.is_valid():
            form.save()
            messages.success(request, "Caixa atualizado!")
            return redirect('financeiro:lista_caixas')
    else:
        form = CaixaForm(instance=caixa)
    return render(request, 'financeiro/caixa_form.html', {'form': form})

@login_required
def excluir_caixa(request, id):
    caixa = get_object_or_404(Caixa, id=id, empresa=request.user.empresa)
    if caixa.lancamento_set.exists():
        messages.error(request, "Não é possível excluir: existem lançamentos.")
    else:
        caixa.delete()
        messages.success(request, "Caixa excluído.")
    return redirect('financeiro:lista_caixas')

@login_required
def definir_caixa_padrao(request, id):
    get_object_or_404(Caixa, id=id, empresa=request.user.empresa)
    ParametroSistema.objects.update_or_create(empresa=request.user.empresa, chave='CAIXA_PADRAO_ID', defaults={'valor': str(id)})
    messages.success(request, "Caixa padrão definido!")
    return redirect('financeiro:lista_caixas')

@login_required
def lista_plano_de_contas(request):
    contas = PlanoDeContas.objects.filter(empresa=request.user.empresa).order_by('codigo')
    return render(request, 'financeiro/plano_de_contas_list.html', {'planos_de_contas': contas})

@login_required
def adicionar_plano_de_contas(request):
    if request.method == 'POST':
        form = PlanoContasForm(request.POST, user=request.user)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.empresa = request.user.empresa
            conta.save()
            messages.success(request, "Categoria criada!")
            return redirect('financeiro:lista_plano_de_contas')
    else:
        form = PlanoContasForm(user=request.user)
    return render(request, 'financeiro/plano_de_contas_form.html', {'form': form})

@login_required
def editar_plano_de_contas(request, id):
    conta = get_object_or_404(PlanoDeContas, id=id, empresa=request.user.empresa)
    if request.method == 'POST':
        form = PlanoContasForm(request.POST, instance=conta, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria atualizada!")
            return redirect('financeiro:lista_plano_de_contas')
    else:
        form = PlanoContasForm(instance=conta, user=request.user)
    return render(request, 'financeiro/plano_de_contas_form.html', {'form': form})

@login_required
def excluir_plano_de_contas(request, id):
    conta = get_object_or_404(PlanoDeContas, id=id, empresa=request.user.empresa)
    if conta.lancamento_set.exists() or conta.conta_set.exists():
        messages.error(request, "Não é possível excluir: existem lançamentos usando esta categoria.")
    else:
        conta.delete()
        messages.success(request, "Categoria excluída.")
    return redirect('financeiro:lista_plano_de_contas')

@login_required
def lista_formas_pagamento(request):
    formas = FormaPagamento.objects.filter(empresa=request.user.empresa)
    return render(request, 'financeiro/formas_pagamento_list.html', {'formas': formas})

@login_required
def nova_forma_pagamento(request):
    if request.method == 'POST':
        form = FormaPagamentoForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.empresa = request.user.empresa
            f.save()
            messages.success(request, "Forma de pagamento cadastrada!")
            return redirect('financeiro:lista_formas_pagamento')
    else:
        form = FormaPagamentoForm()
    return render(request, 'financeiro/formas_pagamento_form.html', {'form': form, 'titulo': 'Nova Forma de Pagamento'})

@login_required
def fluxo_caixa(request):
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    data_inicio = request.GET.get('data_inicio') or inicio_mes.strftime('%Y-%m-%d')
    data_fim = request.GET.get('data_fim') or hoje.strftime('%Y-%m-%d')
    parametro_caixa_get = request.GET.get('caixa')
    caixa_id = None
    if parametro_caixa_get is not None:
        if parametro_caixa_get != '': caixa_id = int(parametro_caixa_get)
    else:
        try:
            param = ParametroSistema.objects.get(empresa=request.user.empresa, chave='CAIXA_PADRAO_ID')
            if param.valor and param.valor.isdigit(): caixa_id = int(param.valor)
        except ParametroSistema.DoesNotExist: pass
    categoria_id_str = request.GET.get('categoria')
    saldo_inicial_cadastro = 0
    if not categoria_id_str:
        if caixa_id:
            caixa_obj = Caixa.objects.filter(id=caixa_id, empresa=request.user.empresa).first()
            if caixa_obj: saldo_inicial_cadastro = caixa_obj.saldo_inicial
        else:
            saldo_inicial_cadastro = Caixa.objects.filter(empresa=request.user.empresa).aggregate(Sum('saldo_inicial'))['saldo_inicial__sum'] or 0
    movimentos_anteriores = Lancamento.objects.filter(empresa=request.user.empresa, data_lancamento__lt=data_inicio)
    if caixa_id: movimentos_anteriores = movimentos_anteriores.filter(caixa_id=caixa_id)
    if categoria_id_str: movimentos_anteriores = movimentos_anteriores.filter(plano_de_contas_id=categoria_id_str)
    total_anteriores = movimentos_anteriores.aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_anterior = saldo_inicial_cadastro + total_anteriores
    lancamentos = Lancamento.objects.filter(empresa=request.user.empresa, data_lancamento__range=[data_inicio, data_fim])
    if caixa_id: lancamentos = lancamentos.filter(caixa_id=caixa_id)
    if categoria_id_str: lancamentos = lancamentos.filter(plano_de_contas_id=categoria_id_str)
    lancamentos = lancamentos.order_by('-data_lancamento')
    total_periodo = lancamentos.aggregate(Sum('valor'))['valor__sum'] or 0
    saldo_final = saldo_anterior + total_periodo
    caixas = Caixa.objects.filter(empresa=request.user.empresa)
    categorias = PlanoDeContas.objects.filter(empresa=request.user.empresa).order_by('nome')
    return render(request, 'financeiro/fluxo_lista.html', {'lancamentos': lancamentos, 'saldo_anterior': saldo_anterior, 'saldo_final': saldo_final, 'caixas': caixas, 'categorias': categorias, 'caixa_selecionado_id': str(caixa_id) if caixa_id else '', 'categoria_selecionada_id': categoria_id_str or '', 'data_inicio': data_inicio, 'data_fim': data_fim})

@login_required
def novo_lancamento_manual(request):
    if request.method == 'POST':
        form = LancamentoManualForm(request.POST, user=request.user)
        if form.is_valid():
            lancamento = form.save(commit=False)
            lancamento.empresa = request.user.empresa
            lancamento.save()
            messages.success(request, "Lançamento registrado!")
            return redirect('financeiro:fluxo_caixa')
    else:
        form = LancamentoManualForm(user=request.user)
    return render(request, 'financeiro/lancamento_form.html', {'form': form})

@login_required
def editar_lancamento(request, id):
    lancamento = get_object_or_404(Lancamento, id=id, empresa=request.user.empresa)
    if request.method == 'POST':
        form = LancamentoManualForm(request.POST, instance=lancamento, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Lançamento atualizado!")
            return redirect('financeiro:fluxo_caixa')
    else:
        form = LancamentoManualForm(instance=lancamento, user=request.user)
    return render(request, 'financeiro/lancamento_form.html', {'form': form})

@login_required
def excluir_lancamento(request, id):
    lancamento = get_object_or_404(Lancamento, id=id, empresa=request.user.empresa)
    if lancamento.conta_origem:
        lancamento.conta_origem.status = 'PENDENTE'
        lancamento.conta_origem.save()
    lancamento.delete()
    messages.success(request, "Lançamento excluído.")
    return redirect('financeiro:fluxo_caixa')

def processar_lancamento_conta(request, form, tipo_redirect):
    dados = form.cleaned_data
    descricao_original = dados['descricao']
    valor_original = dados['valor']
    vencimento_inicial = dados['data_vencimento']
    gerar_parcelas = dados.get('gerar_parcelas')
    if gerar_parcelas:
        qtd = dados['qtd_parcelas']
        juros = dados.get('taxa_juros') or Decimal(0)
        valor_total = valor_original + (valor_original * (juros / Decimal(100)))
        valor_parcela = valor_total / qtd
        grupo_parcela = random.randint(1000, 9999)
        for i in range(qtd):
            nova_conta = form.save(commit=False)
            nova_conta.pk = None
            nova_conta.empresa = request.user.empresa
            nova_conta.descricao = descricao_original
            nova_conta.documento = f"{grupo_parcela}-{i+1}/{qtd}"
            nova_conta.valor = valor_parcela
            nova_conta.data_vencimento = add_months(vencimento_inicial, i)
            nova_conta.save()
        messages.success(request, f"{qtd} parcelas geradas!")
    else:
        conta = form.save(commit=False)
        conta.empresa = request.user.empresa
        conta.documento = str(random.randint(10000, 99999))
        conta.save()
        messages.success(request, "Lançamento salvo!")
    return redirect(tipo_redirect)

@login_required
def nova_receita(request):
    if request.method == 'POST':
        form = ContaForm(request.POST, user=request.user, tipo_filtro='R')
        if form.is_valid(): return processar_lancamento_conta(request, form, 'financeiro:lista_receber')
    else:
        form = ContaForm(user=request.user, tipo_filtro='R')
    return render(request, 'financeiro/conta_form.html', {'form': form, 'titulo': 'Novo Recebimento'})

@login_required
def nova_despesa(request):
    if request.method == 'POST':
        form = ContaForm(request.POST, user=request.user, tipo_filtro='D')
        if form.is_valid(): return processar_lancamento_conta(request, form, 'financeiro:lista_pagar')
    else:
        form = ContaForm(user=request.user, tipo_filtro='D')
    return render(request, 'financeiro/conta_form.html', {'form': form, 'titulo': 'Nova Despesa'})

@login_required
def lista_contas_receber(request):
    contas = Conta.objects.filter(empresa=request.user.empresa, plano_de_contas__tipo='R')
    data_ini = request.GET.get('data_ini')
    data_fim = request.GET.get('data_fim')
    status = request.GET.get('status')
    if data_ini and data_fim: contas = contas.filter(data_vencimento__range=[data_ini, data_fim])
    if status:
        if status == 'ATRASADA': contas = contas.filter(status='PENDENTE', data_vencimento__lt=date.today())
        else: contas = contas.filter(status=status)
    caixas = Caixa.objects.filter(empresa=request.user.empresa)
    categorias = PlanoDeContas.objects.filter(empresa=request.user.empresa, tipo='R').order_by('nome')
    return render(request, 'financeiro/contas_lista.html', {'contas': contas.order_by('data_vencimento'), 'caixas': caixas, 'categorias': categorias, 'titulo': 'Contas a Receber', 'tipo_lista': 'receber', 'filtro_data_ini': data_ini, 'filtro_data_fim': data_fim, 'filtro_status': status})

@login_required
def lista_contas_pagar(request):
    contas = Conta.objects.filter(empresa=request.user.empresa, plano_de_contas__tipo='D')
    data_ini = request.GET.get('data_ini')
    data_fim = request.GET.get('data_fim')
    status = request.GET.get('status')
    if data_ini and data_fim: contas = contas.filter(data_vencimento__range=[data_ini, data_fim])
    if status:
        if status == 'ATRASADA': contas = contas.filter(status='PENDENTE', data_vencimento__lt=date.today())
        else: contas = contas.filter(status=status)
    caixas = Caixa.objects.filter(empresa=request.user.empresa)
    categorias = PlanoDeContas.objects.filter(empresa=request.user.empresa, tipo='D').order_by('nome')
    return render(request, 'financeiro/contas_lista.html', {'contas': contas.order_by('data_vencimento'), 'caixas': caixas, 'categorias': categorias, 'titulo': 'Contas a Pagar', 'tipo_lista': 'pagar', 'filtro_data_ini': data_ini, 'filtro_data_fim': data_fim, 'filtro_status': status})

@login_required
def baixar_conta(request, id):
    conta = get_object_or_404(Conta, id=id, empresa=request.user.empresa)
    if request.method == 'POST':
        caixa_id = request.POST.get('caixa')
        data_pagamento = request.POST.get('data_pagamento')
        novo_documento = request.POST.get('documento_baixa')
        if not caixa_id or not data_pagamento:
            messages.error(request, "Preencha todos os campos.")
            return redirect('financeiro:lista_receber' if conta.plano_de_contas.tipo == 'R' else 'financeiro:lista_pagar')
        caixa = get_object_or_404(Caixa, id=caixa_id, empresa=request.user.empresa)
        if novo_documento: conta.documento = novo_documento
        conta.status = 'PAGA'
        conta.save()
        Lancamento.objects.create(empresa=request.user.empresa, caixa=caixa, plano_de_contas=conta.plano_de_contas, conta_origem=conta, descricao=f"Baixa: {conta.descricao}", data_lancamento=data_pagamento, valor=conta.valor, tipo='C' if conta.plano_de_contas.tipo == 'R' else 'D')
        messages.success(request, "Baixa realizada!")
        return redirect('financeiro:lista_receber' if conta.plano_de_contas.tipo == 'R' else 'financeiro:lista_pagar')
    return redirect('financeiro:lista_receber')

@login_required
def editar_conta(request, id):
    conta = get_object_or_404(Conta, id=id, empresa=request.user.empresa)
    tipo_filtro = conta.plano_de_contas.tipo
    if request.method == 'POST':
        form = ContaForm(request.POST, instance=conta, user=request.user, tipo_filtro=tipo_filtro)
        if form.is_valid():
            form.save()
            messages.success(request, "Conta atualizada.")
            return redirect('financeiro:lista_receber' if tipo_filtro == 'R' else 'financeiro:lista_pagar')
    else:
        form = ContaForm(instance=conta, user=request.user, tipo_filtro=tipo_filtro)
    return render(request, 'financeiro/conta_form.html', {'form': form})

@login_required
def excluir_conta(request, id):
    conta = get_object_or_404(Conta, id=id, empresa=request.user.empresa)
    if conta.status == 'PAGA':
        messages.error(request, "Não é possível excluir uma conta já paga.")
    else:
        conta.delete()
        messages.success(request, "Conta excluída.")
    return redirect('financeiro:lista_receber' if conta.plano_de_contas.tipo == 'R' else 'financeiro:lista_pagar')
