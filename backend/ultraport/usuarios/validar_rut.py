from django.core.exceptions import ValidationError
def limpiar_rut(rut):
    rut_como_texto = str(rut).strip().upper()
    rut_sin_puntos = rut_como_texto.replace('.', '')
    rut_sin_espacios = rut_sin_puntos.replace(' ', '')
    rut_sin_guion = rut_sin_espacios.replace('-', '')
    return rut_sin_guion

def separar_cuerpo_y_dv(rut):

    rut_limpio = limpiar_rut(rut)

    if len(rut_limpio) < 2:
        raise ValidationError('El RUT es demasiado corto.')

    cuerpo = rut_limpio[:-1]
    digito_verificador = rut_limpio[-1]
    return cuerpo, digito_verificador

def calcular_digito_verificador(cuerpo):
    
    serie_de_factores = [2, 3, 4, 5, 6, 7]
    suma_ponderada = 0
    indice_del_factor = 0

    for caracter in reversed(cuerpo):
        digito = int(caracter)
        factor_actual = serie_de_factores[indice_del_factor]
        suma_ponderada = suma_ponderada + (digito * factor_actual)

        indice_del_factor = (indice_del_factor + 1) % len(serie_de_factores)

    resto = suma_ponderada % 11
    dv_numerico = 11 - resto

    if dv_numerico == 11:
        return '0'
    if dv_numerico == 10:
        return 'K'
    return str(dv_numerico)


def normalizar_rut(rut):
    
    cuerpo, digito_verificador = separar_cuerpo_y_dv(rut)
    return f'{cuerpo}-{digito_verificador}'

def validar_rut_modulo_11(rut):
    
    if rut is None or str(rut).strip() == '':
        raise ValidationError('El RUT es obligatorio.')

    cuerpo, digito_ingresado = separar_cuerpo_y_dv(rut)

    cuerpo_es_solo_numeros = cuerpo.isdigit()
    if not cuerpo_es_solo_numeros:
        raise ValidationError(
            'El cuerpo del RUT solo puede contener números (se permiten puntos y guion).')

    cuerpo_tiene_largo_valido = 7 <= len(cuerpo) <= 8
    if not cuerpo_tiene_largo_valido:
        raise ValidationError(
            'El RUT debe tener entre 7 y 8 dígitos antes del dígito verificador.')

    dv_es_numero_o_k = digito_ingresado.isdigit() or digito_ingresado == 'K'
    if not dv_es_numero_o_k:
        raise ValidationError(
            'El dígito verificador debe ser un número del 0 al 9 o la letra K.')

    digito_esperado = calcular_digito_verificador(cuerpo)
    rut_es_autentico = digito_ingresado == digito_esperado
    if not rut_es_autentico:
        raise ValidationError(
            f'El RUT no es auténtico (Módulo 11). Se esperaba dígito verificador {digito_esperado}.')