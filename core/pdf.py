from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML


def pdf_response(request, template_name, context, filename):
    """Renderiza um template HTML como PDF (A4) e devolve inline no navegador."""
    ctx = dict(context)
    ctx.setdefault('empresa', getattr(request.user, 'empresa', None))
    ctx.setdefault('gerado_em', timezone.localtime(timezone.now()))
    ctx.setdefault('gerado_por', request.user.get_username() if request.user.is_authenticated else '')
    html = render_to_string(template_name, ctx, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp


def nome_arquivo(base):
    return f"{base}-{timezone.localdate().strftime('%Y%m%d')}.pdf"
