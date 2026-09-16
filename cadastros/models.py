from django.db import models
from core.models import ModeloSaaS

class Cadastro(ModeloSaaS):
    PAPEL_CHOICES = [
        ('CLIENTE', 'Cliente'),
        ('FORNECEDOR', 'Fornecedor'),
        ('AMBOS', 'Cliente e Fornecedor'),
    ]

    situacao = models.CharField(max_length=10, choices=[('ATIVO', 'Ativo'), ('INATIVO', 'Inativo')], default='ATIVO')
    papel = models.CharField(max_length=15, choices=PAPEL_CHOICES, default='CLIENTE')
    tipo_pessoa = models.CharField(max_length=2, choices=[('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')], default='PF')

    nome = models.CharField(max_length=255, verbose_name="Nome / Razão Social")
    cpf = models.CharField(max_length=14, blank=True, null=True, verbose_name="CPF")
    cnpj = models.CharField(max_length=18, blank=True, null=True, verbose_name="CNPJ")
    rg = models.CharField(max_length=20, blank=True, null=True)

    email = models.EmailField(blank=True, null=True)
    celular = models.CharField(max_length=20, blank=True, null=True)
    telefone_fixo = models.CharField(max_length=20, blank=True, null=True)

    cep = models.CharField(max_length=10, blank=True, null=True)
    logradouro = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    uf = models.CharField(max_length=2, blank=True, null=True)

    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome
