from django.db import models

class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class ModeloSaaS(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class ParametroSistema(ModeloSaaS):
    chave = models.CharField(max_length=50)
    valor = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.chave}: {self.valor} ({self.empresa.nome})"

    class Meta:
        unique_together = ('empresa', 'chave')
        verbose_name = "Parâmetro do Sistema"
        verbose_name_plural = "Parâmetros do Sistema"
