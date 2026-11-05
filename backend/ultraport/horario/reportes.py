from io import BytesIO

from django.db.models import Q
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .models import ESTADOS_ACTIVOS, NotificacionInasistencia

AZUL = colors.HexColor('#0A1420')
ACENTO = colors.HexColor('#F2A63D')
GRIS = colors.HexColor('#7E90A8')
FILA_ALTA = colors.HexColor('#F4F6F9')
LINEA = colors.HexColor('#D5DCE6')

ETIQUETA_BLOQUE = {
    'primer_turno': '1° turno',
    'segundo_turno': '2° turno',
    'tercer_turno': '3° turno',
}

_ESTILOS = getSampleStyleSheet()
ESTILO_TITULO = ParagraphStyle('titulo', parent=_ESTILOS['Title'], fontSize=16, textColor=AZUL, alignment=TA_LEFT, spaceAfter=4)
ESTILO_SUB = ParagraphStyle('sub', parent=_ESTILOS['Normal'], fontSize=9, textColor=GRIS, spaceAfter=10)
ESTILO_BLOQUE = ParagraphStyle('bloque', parent=_ESTILOS['Heading2'], fontSize=12, textColor=AZUL, spaceBefore=12, spaceAfter=6)
ESTILO_AREA = ParagraphStyle('area', parent=_ESTILOS['Heading3'], fontSize=10, textColor=ACENTO, spaceBefore=8, spaceAfter=4)
ESTILO_PUESTO = ParagraphStyle('puesto', parent=_ESTILOS['Normal'], fontSize=9, textColor=AZUL, spaceBefore=4, spaceAfter=2)
ESTILO_CELDA = ParagraphStyle('celda', parent=_ESTILOS['Normal'], fontSize=8, leading=10)


def _pie(canvas, doc, titulo):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(1.5 * cm, 1 * cm, f'{titulo} · Ultraport')
    canvas.drawRightString(doc.pagesize[0] - 1.5 * cm, 1 * cm, f'Página {doc.page}')
    canvas.restoreState()


def _estilo_tabla(filas):
    estilo = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, LINEA),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    for i in range(2, len(filas), 2):
        estilo.append(('BACKGROUND', (0, i), (-1, i), FILA_ALTA))
    return TableStyle(estilo)


def _tabla_puesto(turno):
    filas = [['ID usuario', 'Contrato', 'Máquina', 'Especialidad', 'Estado']]
    asignaciones = [a for a in turno.asignaciones.all() if a.estado in ESTADOS_ACTIVOS]
    for a in asignaciones:
        u = a.id_usuario
        filas.append([
            Paragraph(str(u.pk), ESTILO_CELDA),
            Paragraph(u.id_contrato.get_tipo_display() if u.id_contrato else '—', ESTILO_CELDA),
            Paragraph(turno.id_maquinaria_req.nombre_maquinaria if turno.id_maquinaria_req else '—', ESTILO_CELDA),
            Paragraph(turno.id_puesto.nombre_puesto, ESTILO_CELDA),
            Paragraph(a.get_estado_display(), ESTILO_CELDA),
        ])
    if not asignaciones:
        filas.append([Paragraph('Sin trabajadores asignados', ESTILO_CELDA), '', '', '', ''])

    tabla = Table(filas, colWidths=[3 * cm, 4 * cm, 5 * cm, 7 * cm, 3 * cm], repeatRows=1)
    tabla.setStyle(_estilo_tabla(filas))
    return tabla, len(asignaciones)


def _agrupar_turnos(malla, bloque_filtro=None):
    turnos = (
        malla.turnos
        .select_related('id_bloque', 'id_area', 'id_puesto', 'id_maquinaria_req')
        .prefetch_related('asignaciones__id_usuario__id_contrato')
        .order_by('id_bloque__orden_secuencia', 'id_area__nombre_area', 'id_puesto__nombre_puesto')
    )
    if bloque_filtro:
        turnos = turnos.filter(id_bloque__nombre_bloque=bloque_filtro)

    bloques = {}
    for t in turnos:
        bloques.setdefault(t.id_bloque, {}).setdefault(t.id_area.nombre_area, []).append(t)
    return bloques


def _documento(buffer, titulo):
    return SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.8 * cm,
        title=titulo, author='Ultraport',
    )


def _respuesta_pdf(buffer, nombre):
    respuesta = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta


def pdf_malla(malla, bloque_filtro=None):
    buffer = BytesIO()
    titulo = f'Horario {malla.fecha:%d-%m-%Y}'
    doc = _documento(buffer, titulo)
    elementos = [
        Paragraph(f'Horario de turnos · {malla.fecha:%d-%m-%Y}', ESTILO_TITULO),
        Paragraph(f'Estado de la malla: {malla.get_estado_display()}', ESTILO_SUB),
    ]

    for bloque, areas in _agrupar_turnos(malla, bloque_filtro).items():
        elementos.append(Paragraph(
            f'{ETIQUETA_BLOQUE.get(bloque.nombre_bloque, bloque.nombre_bloque)} · '
            f'{bloque.hora_inicio:%H:%M} a {bloque.hora_termino:%H:%M}',
            ESTILO_BLOQUE,
        ))
        for area, turnos in areas.items():
            elementos.append(Paragraph(area.upper(), ESTILO_AREA))
            for turno in turnos:
                tabla, n = _tabla_puesto(turno)
                encabezado = Paragraph(
                    f'<b>{turno.id_puesto.nombre_puesto}</b> · {n}/{turno.cupos} cupos',
                    ESTILO_PUESTO,
                )
                elementos.append(KeepTogether([encabezado, tabla, Spacer(1, 6)]))

    doc.build(
        elementos,
        onFirstPage=lambda c, d: _pie(c, d, titulo),
        onLaterPages=lambda c, d: _pie(c, d, titulo),
    )
    sufijo = f'_{bloque_filtro}' if bloque_filtro else ''
    return _respuesta_pdf(buffer, f'horario_{malla.fecha}{sufijo}.pdf')


CABECERA_INASISTENCIAS = ['Fecha registro', 'ID usuario', 'Motivo', 'Desde', 'Hasta', 'Estado', 'ID turno']


def _tabla_inasistencias(registros):
    filas = [CABECERA_INASISTENCIAS]
    for n in registros:
        filas.append([
            Paragraph(n.fecha_registro.strftime('%d-%m-%Y %H:%M') if n.fecha_registro else '', ESTILO_CELDA),
            Paragraph(str(n.id_usuario_id), ESTILO_CELDA),
            Paragraph(n.motivo, ESTILO_CELDA),
            Paragraph(n.fecha_inicio.strftime('%d-%m-%Y'), ESTILO_CELDA),
            Paragraph(n.fecha_fin.strftime('%d-%m-%Y') if n.fecha_fin else n.fecha_inicio.strftime('%d-%m-%Y'), ESTILO_CELDA),
            Paragraph(n.get_estado_display(), ESTILO_CELDA),
            Paragraph(str(n.id_turno) if n.id_turno else '—', ESTILO_CELDA),
        ])
    if not registros:
        filas.append([Paragraph('Sin registros en el rango', ESTILO_CELDA), '', '', '', '', '', ''])

    tabla = Table(filas, colWidths=[3.5 * cm, 2.5 * cm, 8 * cm, 3 * cm, 3 * cm, 3.5 * cm, 2.5 * cm], repeatRows=1)
    tabla.setStyle(_estilo_tabla(filas))
    return tabla


def pdf_inasistencias(desde, hasta, estado=None):
    qs = (
        NotificacionInasistencia.objects
        .filter(fecha_inicio__lte=hasta)
        .filter(Q(fecha_fin__gte=desde) | Q(fecha_fin__isnull=True, fecha_inicio__gte=desde))
        .order_by('fecha_inicio')
    )
    if estado:
        qs = qs.filter(estado=estado)
    registros = list(qs)

    buffer = BytesIO()
    titulo = f'Reporte de inasistencias {desde:%d-%m-%Y} al {hasta:%d-%m-%Y}'
    doc = _documento(buffer, titulo)
    elementos = [
        Paragraph('Reporte de inasistencias', ESTILO_TITULO),
        Paragraph(
            f'Rango: {desde:%d-%m-%Y} al {hasta:%d-%m-%Y} · Registros: {len(registros)}',
            ESTILO_SUB,
        ),
        _tabla_inasistencias(registros),
    ]
    doc.build(
        elementos,
        onFirstPage=lambda c, d: _pie(c, d, titulo),
        onLaterPages=lambda c, d: _pie(c, d, titulo),
    )
    return _respuesta_pdf(buffer, f'inasistencias_{desde}_{hasta}.pdf')