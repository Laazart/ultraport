// Helpers de fecha compartidos por las vistas de día y semana.
// Las fechas viajan como 'YYYY-MM-DD' (hora local, sin zona horaria).

const dos = (n) => String(n).padStart(2, '0');

export const aISO = (d) => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;

export const hoyISO = () => aISO(new Date());

export const desdeISO = (iso) => {
  const [a, m, d] = iso.split('-').map(Number);
  return new Date(a, m - 1, d);
};

export const sumarDias = (iso, dias) => {
  const d = desdeISO(iso);
  d.setDate(d.getDate() + dias);
  return aISO(d);
};

// Lunes de la semana que contiene la fecha (lunes a domingo).
export const lunesDe = (iso) => sumarDias(iso, -((desdeISO(iso).getDay() + 6) % 7));

export const formatearFecha = (iso) => {
  const [a, m, d] = iso.split('-');
  return `${d}-${m}-${a}`;
};

// '2026-11-16' → '16-11'
export const fechaCorta = (iso) => {
  const [, m, d] = iso.split('-');
  return `${d}-${m}`;
};

export const diaSemana = (iso) => desdeISO(iso).toLocaleDateString('es-CL', { weekday: 'long' });

// '2026-11-16' → 'Lun 16-11'
export const diaCorto = (iso) => {
  const nombre = desdeISO(iso).toLocaleDateString('es-CL', { weekday: 'short' }).replace('.', '');
  return `${nombre.charAt(0).toUpperCase()}${nombre.slice(1)} ${fechaCorta(iso)}`;
};

export const rangoHorario = (b) =>
  `${b.hora_inicio} – ${b.hora_termino}${b.cruza_medianoche ? ' (+1 día)' : ''}`;
