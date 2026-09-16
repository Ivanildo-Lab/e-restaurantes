from django import forms
from .models import Mesa, ItemMesa

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'responsavel']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})

class ItemMesaForm(forms.ModelForm):
    class Meta:
        model = ItemMesa
        fields = ['produto', 'quantidade']
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from estoque.models import Produto
            self.fields['produto'].queryset = Produto.objects.filter(empresa=user.empresa)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})
