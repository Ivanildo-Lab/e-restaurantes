from django.db import models
from core.models import ModeloSaaS
from cadastros.models import Cadastro

class PlanoDeContas(ModeloSaaS):
    TIPO_CHOICES = [('R', 'Receita'), ('D', 'Despesa')]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    codigo = models.CharField(max_length=20, blank=True)
    def __str__(self): return f"{self.codigo} - {self.nome}"

class Caixa(ModeloSaaS):
    nome = models.CharField(max_length=100)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return self.nome

class Conta(ModeloSaaS):
    STATUS_CHOICES = [('PENDENTE', 'Pendente'), ('PAGA', 'Paga / Recebida'), ('CANCELADA', 'Cancelada')]
    descricao = models.CharField(max_length=255)
    plano_de_contas = models.ForeignKey(PlanoDeContas, on_delete=models.PROTECT)
    cadastro = models.ForeignKey(Cadastro, on_delete=models.PROTECT, verbose_name="Favorecido", null=True, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    documento = models.CharField(max_length=50, blank=True, null=True)
    observacoes = models.TextField(blank=True)
    arquivo = models.FileField(upload_to='financeiro/contas/', blank=True, null=True)
    def __str__(self): return f"{self.descricao} - {self.valor}"

class Lancamento(ModeloSaaS):
    TIPO_CHOICES = [('C', 'Receita'), ('D', 'Despesa')]
    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT)
    plano_de_contas = models.ForeignKey(PlanoDeContas, on_delete=models.SET_NULL, null=True, blank=True)
    conta_origem = models.OneToOneField(Conta, on_delete=models.SET_NULL, null=True, blank=True)
    data_lancamento = models.DateField()
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)

class FormaPagamento(ModeloSaaS):
    TIPO_CHOICES = [('V', 'À Vista'), ('P', 'A Prazo')]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default='V')
    ativo = models.BooleanField(default=True)
    def __str__(self): return self.nome
