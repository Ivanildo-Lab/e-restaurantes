from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Value
from django.db.models.functions import Replace
from .models import Cadastro
from .forms import CadastroForm

@login_required
def lista_clientes(request):
    queryset = Cadastro.objects.filter(empresa=request.user.empresa, papel__in=['CLIENTE', 'AMBOS']).order_by('nome')
    q = request.GET.get('q')
    if q:
        q_clean = q.replace('.', '').replace('-', '')
        queryset = queryset.annotate(
            cpf_clean=Replace(Replace('cpf', Value('.'), Value('')), Value('-'), Value('')),
        ).filter(Q(nome__icontains=q) | Q(cpf_clean__icontains=q_clean))
    return render(request, 'cadastros/lista.html', {'cadastros': queryset, 'filtro_q': q})

@login_required
def novo_cliente(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.papel = 'CLIENTE'
            obj.save()
            messages.success(request, f"{obj.nome} cadastrado com sucesso!")
            return redirect('lista_clientes')
    else:
        form = CadastroForm(user=request.user)
    return render(request, 'cadastros/formulario.html', {'form': form, 'titulo': 'Novo Cliente'})

@login_required
def editar_cliente(request, pk):
    cadastro = get_object_or_404(Cadastro, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = CadastroForm(request.POST, instance=cadastro, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Cadastro atualizado!")
            return redirect('lista_clientes')
    else:
        form = CadastroForm(instance=cadastro, user=request.user)
    return render(request, 'cadastros/formulario.html', {'form': form, 'titulo': 'Editar Cliente'})

@login_required
def excluir_cliente(request, pk):
    cadastro = get_object_or_404(Cadastro, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        cadastro.delete()
        messages.success(request, "Cadastro excluído.")
    return redirect('lista_clientes')

@login_required
def lista_fornecedores(request):
    queryset = Cadastro.objects.filter(empresa=request.user.empresa, papel__in=['FORNECEDOR', 'AMBOS']).order_by('nome')
    q = request.GET.get('q')
    if q:
        q_clean = q.replace('.', '').replace('-', '')
        queryset = queryset.annotate(
            cpf_clean=Replace(Replace('cpf', Value('.'), Value('')), Value('-'), Value('')),
            cnpj_clean=Replace(Replace('cnpj', Value('.'), Value('')), Value('-'), Value('')),
        ).filter(Q(nome__icontains=q) | Q(cpf_clean__icontains=q_clean) | Q(cnpj_clean__icontains=q_clean))
    return render(request, 'cadastros/lista_fornecedores.html', {'cadastros': queryset})

@login_required
def novo_fornecedor(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.papel = 'FORNECEDOR'
            obj.tipo_pessoa = 'PJ'
            obj.save()
            messages.success(request, "Fornecedor cadastrado!")
            return redirect('lista_fornecedores')
    else:
        form = CadastroForm(user=request.user)
    return render(request, 'cadastros/formulario.html', {'form': form, 'titulo': 'Novo Fornecedor'})
