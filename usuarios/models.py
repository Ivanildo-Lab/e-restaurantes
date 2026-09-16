from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import Empresa

class Usuario(AbstractUser):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username
