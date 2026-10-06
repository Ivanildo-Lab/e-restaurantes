"""Filtros por data em campos DateTime sem depender das tabelas de fuso do MySQL.

O lookup __date do Django gera DATE(CONVERT_TZ(...)), que retorna NULL quando
as tabelas mysql.time_zone* estao vazias — e o filtro passa a retornar 0 linhas
silenciosamente. Aqui convertemos o dia (fuso local) em intervalo UTC em Python.
"""
from datetime import datetime, timedelta
from django.utils import timezone


def intervalo_dia_utc(data_str):
    """'YYYY-MM-DD' -> (inicio_inclusivo, fim_exclusivo) aware em UTC, ou None."""
    try:
        d = datetime.strptime(str(data_str)[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None
    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime(d.year, d.month, d.day), tz)
    return inicio, inicio + timedelta(days=1)


def filtrar_periodo(queryset, campo, data_inicio, data_fim):
    """Aplica filtro inclusivo de dias sobre um campo DateTime."""
    if data_inicio:
        iv = intervalo_dia_utc(data_inicio)
        if iv:
            queryset = queryset.filter(**{f'{campo}__gte': iv[0]})
    if data_fim:
        iv = intervalo_dia_utc(data_fim)
        if iv:
            queryset = queryset.filter(**{f'{campo}__lt': iv[1]})
    return queryset
