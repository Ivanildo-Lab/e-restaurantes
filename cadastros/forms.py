from django import forms
from .models import Cadastro

class CadastroForm(forms.ModelForm):
    class Meta:
        model = Cadastro
        fields = ['nome', 'tipo_pessoa', 'papel', 'cpf', 'cnpj', 'rg', 'email', 'celular', 'telefone_fixo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'observacoes']
        widgets = {'observacoes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full bg-white border-2 border-slate-200 p-3 rounded-xl focus:border-blue-500 outline-none transition-all'})

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf and self.user:
            if Cadastro.objects.filter(empresa=self.user.empresa, cpf=cpf).exclude(id=self.instance.id).exists():
                raise forms.ValidationError("Este CPF já está cadastrado.")
        return cpf

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if cnpj and self.user:
            if Cadastro.objects.filter(empresa=self.user.empresa, cnpj=cnpj).exclude(id=self.instance.id).exists():
                raise forms.ValidationError("Este CNPJ já está cadastrado.")
        return cnpj
