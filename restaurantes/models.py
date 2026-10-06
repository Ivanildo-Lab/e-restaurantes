from django.db import models
from core.models import ModeloSaaS
from django.utils import timezone
from decimal import Decimal

class Mesa(ModeloSaaS):
    STATUS_CHOICES = [('LIVRE', 'Livre'), ('OCUPADA', 'Ocupada')]
    numero = models.CharField(max_length=10)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='LIVRE')
    responsavel = models.CharField(max_length=255, blank=True, default='Consumidor Final')
    data_abertura = models.DateTimeField(null=True, blank=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self): return f"Mesa {self.numero}"

    def total_atual(self):
        # Soma APENAS a sessao ABERTA — sessoes FECHADAS ficam preservadas p/ auditoria
        from django.db.models import Sum
        total = self.itemmesa_set.filter(ocupacao__status='ABERTA').aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')

    def total_itens(self):
        return self.itemmesa_set.filter(ocupacao__status='ABERTA').count()

class MesaOcupacao(ModeloSaaS):
    STATUS_CHOICES = [('ABERTA', 'Aberta'), ('FECHADA', 'Fechada')]
    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, related_name='ocupacoes')
    responsavel = models.CharField(max_length=255, blank=True, default='Consumidor Final')
    data_abertura = models.DateTimeField(default=timezone.now)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_recebido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    troco = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTA')

    class Meta:
        ordering = ['-data_abertura']

    def __str__(self):
        return f"Ocupacao #{self.id} - Mesa {self.mesa.numero} ({self.status})"

    def total_atual(self):
        from django.db.models import Sum
        total = self.itens.aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')

    def total_itens(self):
        return self.itens.count()

    @property
    def documento_financeiro(self):
        return f"OCUP-{self.id}"


class ItemMesa(ModeloSaaS):
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE)
    ocupacao = models.ForeignKey(MesaOcupacao, on_delete=models.CASCADE, related_name='itens', null=True, blank=True)
    produto = models.ForeignKey('estoque.Produto', on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self): return f"{self.quantidade}x {self.produto.nome} - Mesa {self.mesa.numero} (Ocup #{self.ocupacao_id})"

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.quantidade)) * self.valor_unitario
        super().save(*args, **kwargs)
