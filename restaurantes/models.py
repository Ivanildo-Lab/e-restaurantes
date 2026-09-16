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
        from django.db.models import Sum
        total = self.itemmesa_set.aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')

    def total_itens(self):
        return self.itemmesa_set.count()

class ItemMesa(ModeloSaaS):
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE)
    produto = models.ForeignKey('estoque.Produto', on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self): return f"{self.quantidade}x {self.produto.nome} - Mesa {self.mesa.numero}"

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.quantidade)) * self.valor_unitario
        super().save(*args, **kwargs)
