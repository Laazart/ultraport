export const validarRut = (rutCompleto) => {
  if (!rutCompleto) return false;
  
  // Limpiamos el formato (quitamos puntos y guiones)
  const rutLimpio = rutCompleto.replace(/[^0-9kK]/g, '').toUpperCase();
  
  if (rutLimpio.length < 8) return false;

  const cuerpo = rutLimpio.slice(0, -1);
  const dvIngresado = rutLimpio.slice(-1);

  let suma = 0;
  let multiplicador = 2;

  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma += parseInt(cuerpo.charAt(i)) * multiplicador;
    multiplicador = multiplicador === 7 ? 2 : multiplicador + 1;
  }

  const dvEsperado = 11 - (suma % 11);
  const dvCalculado = dvEsperado === 11 ? '0' : dvEsperado === 10 ? 'K' : dvEsperado.toString();

  return dvIngresado === dvCalculado;
};