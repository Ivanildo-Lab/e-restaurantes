from django.db import models
from core.models import ModeloSaaS

class Categoria(ModeloSaaS):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True)
    ordem = models.IntegerField(default=0, verbose_name="Ordem de Exibição")

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome

class Produto(ModeloSaaS):
    TIPO_CHOICES = [('P', 'Produto'), ('S', 'Serviço')]
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default='P')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoria")
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    valor_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    estoque_deposito = models.IntegerField(default=0)
    estoque_minimo = models.IntegerField(default=5)
    def __str__(self): return f"{'[SERV]' if self.tipo == 'S' else '[PROD]'} {self.nome}"

class MovimentacaoEstoque(ModeloSaaS):
    TIPO_MOV = [('E', 'Entrada'), ('S', 'Saída')]
    FORMA_PAGAMENTO = [('V', 'À Vista'), ('P', 'A Prazo')]
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField()
    tipo = models.CharField(max_length=1, choices=TIPO_MOV)
    fornecedor = models.ForeignKey('cadastros.Cadastro', on_delete=models.PROTECT, null=True, blank=True)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    forma_pagamento = models.CharField(max_length=1, choices=FORMA_PAGAMENTO, null=True, blank=True)
    num_parcelas = models.IntegerField(default=1)
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True)

    @property
    def total(self):
        return self.quantidade * self.valor_unitario

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.tipo == 'E':
                self.produto.estoque_deposito += self.quantidade
                self.produto.valor_custo = self.valor_unitario
            else:
                self.produto.estoque_deposito -= self.quantidade
            self.produto.save()
        super().save(*args, **kwargs)
