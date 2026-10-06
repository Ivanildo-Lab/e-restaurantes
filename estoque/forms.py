from django import forms
from .models import Produto, MovimentacaoEstoque, Categoria
from core.widgets import AutoCompleteWidget

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'descricao', 'ordem']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['tipo', 'categoria', 'nome', 'valor_custo', 'preco_venda', 'estoque_minimo']
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['categoria'].queryset = Categoria.objects.filter(empresa=user.empresa)
        self.fields['categoria'].required = False
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})

class MovimentacaoForm(forms.ModelForm):
    caixa_pagamento = forms.ModelChoiceField(queryset=None, required=False, label="Caixa de Saída")
    class Meta:
        model = MovimentacaoEstoque
        fields = ['produto', 'fornecedor', 'quantidade', 'valor_unitario', 'tipo', 'forma_pagamento', 'num_parcelas', 'observacao']
        widgets = {
            'produto': AutoCompleteWidget(api_url='/api/buscar/produto/', placeholder='Buscar produto...'),
            'fornecedor': AutoCompleteWidget(api_url='/api/buscar/cadastro/', placeholder='Buscar fornecedor...'),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['produto'].queryset = Produto.objects.filter(empresa=user.empresa, tipo='P')
            self.fields['fornecedor'].queryset = __import__('cadastros.models', fromlist=['Cadastro']).Cadastro.objects.filter(empresa=user.empresa, papel__in=['FORNECEDOR', 'AMBOS'])
            self.fields['caixa_pagamento'].queryset = __import__('financeiro.models', fromlist=['Caixa']).Caixa.objects.filter(empresa=user.empresa)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})
