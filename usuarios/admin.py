from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Empresa', {'fields': ('empresa', 'telefone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Empresa', {'fields': ('empresa', 'telefone')}),
    )
    list_display = ('username', 'email', 'empresa', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'empresa')
