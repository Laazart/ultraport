"""Reportes exportables (RF-19, RF-20, RF-21) en PDF y Excel.

Los datos de cada reporte se arman una sola vez (columnas + filas) y luego se
renderizan a PDF (ReportLab) o a Excel (openpyxl), para que ambos formatos
muestren exactamente lo mismo.
"""
from io import BytesIO

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .models import ESTADOS_ACTIVOS, NotificacionInasistencia

CONTENT_TYPE_PDF = 'application/pdf'
CONTENT_TYPE_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

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

SIN_ASIGNAR = 'Sin trabajadores asignados'

_ESTILOS = getSampleStyleSheet()
ESTILO_TITULO = ParagraphStyle('titulo', parent=_ESTILOS['Title'], fontSize=16, textColor=AZUL, alignment=TA_LEFT, spaceAfter=4)
ESTILO_SUB = ParagraphStyle('sub', parent=_ESTILOS['Normal'], fontSize=9, textColor=GRIS, spaceAfter=10)
ESTILO_BLOQUE = ParagraphStyle('bloque', parent=_ESTILOS['Heading2'], fontSize=12, textColor=AZUL, spaceBefore=12, spaceAfter=6)
ESTILO_AREA = ParagraphStyle('area', parent=_ESTILOS['Heading3'], fontSize=10, textColor=ACENTO, spaceBefore=8, spaceAfter=4)
ESTILO_PUESTO = ParagraphStyle('puesto', parent=_ESTILOS['Normal'], fontSize=9, textColor=AZUL, spaceBefore=4, spaceAfter=2)
ESTILO_CELDA = ParagraphStyle('celda', parent=_ESTILOS['Normal'], fontSize=8, leading=10)

# Columnas y anchos (cm) de las tablas. Ancho útil de A4 apaisado: 26,7 cm.
COLUMNAS_MALLA_COMPLETA = [
    ('Código', 1.5), ('Nombre', 4.5), ('RUT', 2.5), ('Correo', 5.5),
    ('Contrato', 3), ('Función', 4.5), ('Máquina', 3.2), ('Estado', 2),
]
# Lo que puede descargar un trabajador: sin RUT ni correo de otros.
COLUMNAS_MALLA_RESTRINGIDA = [
    ('Código', 2), ('Nombre', 8), ('Función', 8), ('Máquina', 8.7),
]
COLUMNAS_INASISTENCIAS = [
    ('Fecha registro', 2.8), ('Nombre', 4), ('RUT', 2.3), ('Correo', 4.8),
    ('Motivo', 5.6), ('Desde', 2), ('Hasta', 2), ('Estado', 2), ('Turno', 1.2),
]


def columnas_malla(completo):
    return COLUMNAS_MALLA_COMPLETA if completo else COLUMNAS_MALLA_RESTRINGIDA


def _nombre(usuario):
    return f'{usuario.nombres} {usuario.apellidos}'


# ---------------------------------------------------------------- datos

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
        area = t.id_area.nombre_area if t.id_area else 'Sin área'
        bloques.setdefault(t.id_bloque, {}).setdefault(area, []).append(t)
    return bloques


def _asignaciones_activas(turno):
    return [a for a in turno.asignaciones.all() if a.estado in ESTADOS_ACTIVOS]


def _datos_asignacion(turno, asignacion):
    u = asignacion.id_usuario
    return {
        'Código': str(u.pk),
        'Nombre': _nombre(u),
        'RUT': u.rut,
        'Correo': u.correo,
        'Contrato': u.id_contrato.get_tipo_display() if u.id_contrato else '—',
        'Función': turno.id_puesto.nombre_puesto,
        'Máquina': turno.id_maquinaria_req.nombre_maquinaria if turno.id_maquinaria_req else '—',
        'Estado': asignacion.get_estado_display(),
    }


def _fila(datos, columnas):
    return [datos.get(nombre, '') for nombre, _ in columnas]


def _etiqueta_bloque(bloque):
    return ETIQUETA_BLOQUE.get(bloque.nombre_bloque, bloque.nombre_bloque)


def _horario_bloque(bloque):
    return f'{bloque.hora_inicio:%H:%M} a {bloque.hora_termino:%H:%M}'


def inasistencias_en_rango(desde, hasta, estado=None):
    """Avisos cuyo período [fecha_inicio, fecha_fin] se cruza con [desde, hasta]."""
    qs = (
        NotificacionInasistencia.objects
        .select_related('id_usuario')
        .filter(fecha_inicio__lte=hasta)
        .filter(Q(fecha_fin__gte=desde) | Q(fecha_fin__isnull=True, fecha_inicio__gte=desde))
        .order_by('fecha_inicio', 'id_notificacion')
    )
    if estado:
        qs = qs.filter(estado=estado)
    return list(qs)


def _datos_inasistencia(n):
    u = n.id_usuario
    return {
        'Fecha registro': timezone.localtime(n.fecha_registro).replace(tzinfo=None) if n.fecha_registro else None,
        'Nombre': _nombre(u),
        'RUT': u.rut,
        'Correo': u.correo,
        'Motivo': n.motivo,
        'Desde': n.fecha_inicio,
        'Hasta': n.fecha_fin or n.fecha_inicio,
        'Estado': n.get_estado_display(),
        'Turno': str(n.id_turno) if n.id_turno else '—',
    }


# ---------------------------------------------------------------- PDF

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


def _texto_pdf(valor):
    if valor is None:
        return ''
    if hasattr(valor, 'hour'):
        return valor.strftime('%d-%m-%Y %H:%M')
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d-%m-%Y')
    return str(valor)


def _tabla_pdf(columnas, filas_datos, texto_vacio):
    filas = [[nombre for nombre, _ in columnas]]
    for fila in filas_datos:
        filas.append([Paragraph(_texto_pdf(v), ESTILO_CELDA) for v in fila])
    if not filas_datos:
        filas.append([Paragraph(texto_vacio, ESTILO_CELDA)] + [''] * (len(columnas) - 1))
    tabla = Table(filas, colWidths=[ancho * cm for _, ancho in columnas], repeatRows=1)
    tabla.setStyle(_estilo_tabla(filas))
    return tabla


def _documento(buffer, titulo):
    return SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.8 * cm,
        title=titulo, author='Ultraport',
    )


def _respuesta(contenido, content_type, nombre):
    respuesta = HttpResponse(contenido, content_type=content_type)
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta


def _construir_pdf(titulo, elementos):
    buffer = BytesIO()
    _documento(buffer, titulo).build(
        elementos,
        onFirstPage=lambda c, d: _pie(c, d, titulo),
        onLaterPages=lambda c, d: _pie(c, d, titulo),
    )
    return buffer.getvalue()


def _nombre_archivo_malla(malla, bloque_filtro, extension):
    sufijo = f'_{bloque_filtro}' if bloque_filtro else ''
    return f'horario_{malla.fecha}{sufijo}.{extension}'


def pdf_malla(malla, bloque_filtro=None, completo=True):
    columnas = columnas_malla(completo)
    titulo = f'Horario {malla.fecha:%d-%m-%Y}'
    elementos = [
        Paragraph(f'Horario de turnos · {malla.fecha:%d-%m-%Y}', ESTILO_TITULO),
        Paragraph(f'Estado de la malla: {malla.get_estado_display()}', ESTILO_SUB),
    ]

    for bloque, areas in _agrupar_turnos(malla, bloque_filtro).items():
        elementos.append(Paragraph(f'{_etiqueta_bloque(bloque)} · {_horario_bloque(bloque)}', ESTILO_BLOQUE))
        for area, turnos in areas.items():
            elementos.append(Paragraph(area.upper(), ESTILO_AREA))
            for turno in turnos:
                asignaciones = _asignaciones_activas(turno)
                filas = [_fila(_datos_asignacion(turno, a), columnas) for a in asignaciones]
                encabezado = Paragraph(
                    f'<b>{turno.id_puesto.nombre_puesto}</b> · {len(asignaciones)}/{turno.cupos} cupos',
                    ESTILO_PUESTO,
                )
                tabla = _tabla_pdf(columnas, filas, SIN_ASIGNAR)
                elementos.append(KeepTogether([encabezado, tabla, Spacer(1, 6)]))

    return _respuesta(
        _construir_pdf(titulo, elementos), CONTENT_TYPE_PDF,
        _nombre_archivo_malla(malla, bloque_filtro, 'pdf'),
    )


def pdf_inasistencias(desde, hasta, estado=None):
    registros = inasistencias_en_rango(desde, hasta, estado)
    filas = [_fila(_datos_inasistencia(n), COLUMNAS_INASISTENCIAS) for n in registros]
    titulo = f'Reporte de inasistencias {desde:%d-%m-%Y} al {hasta:%d-%m-%Y}'
    elementos = [
        Paragraph('Reporte de inasistencias', ESTILO_TITULO),
        Paragraph(
            f'Rango: {desde:%d-%m-%Y} al {hasta:%d-%m-%Y} · Registros: {len(registros)}',
            ESTILO_SUB,
        ),
        _tabla_pdf(COLUMNAS_INASISTENCIAS, filas, 'Sin registros en el rango'),
    ]
    return _respuesta(
        _construir_pdf(titulo, elementos), CONTENT_TYPE_PDF,
        f'inasistencias_{desde}_{hasta}.pdf',
    )


# ---------------------------------------------------------------- Excel

_XLSX_RELLENO_ENCABEZADO = PatternFill('solid', fgColor='0A1420')
_XLSX_FUENTE_ENCABEZADO = Font(bold=True, color='FFFFFF')
_XLSX_FILA_ENCABEZADO = 4
_XLSX_FORMATO = {'fecha': 'DD-MM-YYYY', 'fecha_hora': 'DD-MM-YYYY HH:MM'}


def _libro_xlsx(titulo_hoja, titulo, subtitulo, columnas, filas):
    """Hoja con título (fila 1), subtítulo (fila 2) y la tabla desde la fila 4."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo_hoja
    hoja['A1'] = titulo
    hoja['A1'].font = Font(bold=True, size=14, color='0A1420')
    hoja['A2'] = subtitulo
    hoja['A2'].font = Font(italic=True, color='7E90A8')

    for i, (nombre, ancho) in enumerate(columnas, start=1):
        celda = hoja.cell(row=_XLSX_FILA_ENCABEZADO, column=i, value=nombre)
        celda.fill = _XLSX_RELLENO_ENCABEZADO
        celda.font = _XLSX_FUENTE_ENCABEZADO
        celda.alignment = Alignment(vertical='center')
        hoja.column_dimensions[get_column_letter(i)].width = max(12, ancho * 5)

    for r, fila in enumerate(filas, start=_XLSX_FILA_ENCABEZADO + 1):
        for c, valor in enumerate(fila, start=1):
            celda = hoja.cell(row=r, column=c, value=valor)
            if hasattr(valor, 'hour'):
                celda.number_format = _XLSX_FORMATO['fecha_hora']
            elif hasattr(valor, 'strftime'):
                celda.number_format = _XLSX_FORMATO['fecha']

    ultima_fila = _XLSX_FILA_ENCABEZADO + max(len(filas), 1)
    hoja.auto_filter.ref = f'A{_XLSX_FILA_ENCABEZADO}:{get_column_letter(len(columnas))}{ultima_fila}'
    hoja.freeze_panes = f'A{_XLSX_FILA_ENCABEZADO + 1}'

    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


COLUMNAS_XLSX_MALLA_PREFIJO = [('Bloque', 2), ('Horario', 2.5), ('Área', 3), ('Cupos', 1.5)]


def xlsx_malla(malla, bloque_filtro=None, completo=True):
    columnas_persona = columnas_malla(completo)
    columnas = COLUMNAS_XLSX_MALLA_PREFIJO + columnas_persona
    filas = []
    for bloque, areas in _agrupar_turnos(malla, bloque_filtro).items():
        for area, turnos in areas.items():
            for turno in turnos:
                asignaciones = _asignaciones_activas(turno)
                prefijo = [
                    _etiqueta_bloque(bloque), _horario_bloque(bloque), area,
                    f'{len(asignaciones)}/{turno.cupos}',
                ]
                if not asignaciones:
                    vacio = {'Nombre': SIN_ASIGNAR, 'Función': turno.id_puesto.nombre_puesto}
                    filas.append(prefijo + _fila(vacio, columnas_persona))
                for a in asignaciones:
                    filas.append(prefijo + _fila(_datos_asignacion(turno, a), columnas_persona))

    contenido = _libro_xlsx(
        'Horario',
        f'Horario de turnos · {malla.fecha:%d-%m-%Y}',
        f'Estado de la malla: {malla.get_estado_display()}',
        columnas, filas,
    )
    return _respuesta(contenido, CONTENT_TYPE_XLSX, _nombre_archivo_malla(malla, bloque_filtro, 'xlsx'))


def xlsx_inasistencias(desde, hasta, estado=None):
    registros = inasistencias_en_rango(desde, hasta, estado)
    filas = [_fila(_datos_inasistencia(n), COLUMNAS_INASISTENCIAS) for n in registros]
    contenido = _libro_xlsx(
        'Inasistencias',
        'Reporte de inasistencias',
        f'Rango: {desde:%d-%m-%Y} al {hasta:%d-%m-%Y} · Registros: {len(registros)}',
        COLUMNAS_INASISTENCIAS, filas,
    )
    return _respuesta(contenido, CONTENT_TYPE_XLSX, f'inasistencias_{desde}_{hasta}.xlsx')
