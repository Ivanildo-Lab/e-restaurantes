from django.db import models
from django.utils import timezone
from decimal import Decimal
from core.models import ModeloSaaS


class Venda(ModeloSaaS):
    STATUS_CHOICES = [('ABERTA', 'Aberta'), ('FINALIZADA', 'Finalizada'), ('CANCELADA', 'Cancelada')]
    cliente = models.CharField(max_length=255, blank=True, default='Consumidor Final')
    data_venda = models.DateTimeField(default=timezone.now)
    data_finalizacao = models.DateTimeField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_recebido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    troco = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    forma_pagamento = models.ForeignKey('financeiro.FormaPagamento', on_delete=models.PROTECT, null=True, blank=True)
    caixa = models.ForeignKey('financeiro.Caixa', on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTA')

    class Meta:
        ordering = ['-data_venda']

    def __str__(self):
        return f"Venda #{self.id} - R$ {self.valor_total} ({self.status})"

    def total_atual(self):
        from django.db.models import Sum
        total = self.itens.aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')

    def total_itens(self):
        return self.itens.count()

    @property
    def documento_financeiro(self):
        return f"PDV-{self.id}"


class ItemVenda(ModeloSaaS):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey('estoque.Produto', on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} - Venda #{self.venda_id}"

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.quantidade)) * self.valor_unitario
        super().save(*args, **kwargs)
