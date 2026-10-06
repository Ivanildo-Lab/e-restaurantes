from django import forms
from .models import Mesa, ItemMesa
from core.widgets import AutoCompleteWidget

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'responsavel']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].required = False
        self.fields['responsavel'].widget.attrs.update({'placeholder': 'Consumidor Final'})
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].required = False
        self.fields['responsavel'].widget.attrs.update({'placeholder': 'Consumidor Final'})
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})

class ItemMesaForm(forms.ModelForm):
    class Meta:
        model = ItemMesa
        fields = ['produto', 'quantidade']
        widgets = {
            'produto': AutoCompleteWidget(api_url='/api/buscar/produto/', placeholder='Buscar produto...'),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from estoque.models import Produto
            self.fields['produto'].queryset = Produto.objects.filter(empresa=user.empresa)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})
