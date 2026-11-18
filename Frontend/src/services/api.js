import axios from 'axios';

const RAW_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';
export const API_BASE = `${RAW_URL.replace(/\/+$/, '')}/`;

export const TIMEOUT_MS = 15000;
// Subida de adjuntos y descarga de reportes: más lentas, se pasa por llamada.
export const TIMEOUT_ARCHIVOS_MS = 60000;
export const MENSAJE_TIMEOUT = 'El servidor tardó demasiado en responder. Intenta de nuevo.';
export const MENSAJE_SIN_CONEXION = 'No se pudo conectar con el servidor.';

// Instancia única usada por todos los servicios. clarifyTimeoutError hace que
// un timeout llegue como ETIMEDOUT (y no ECONNABORTED, que también es abortar).
const http = axios.create({
  timeout: TIMEOUT_MS,
  transitional: { clarifyTimeoutError: true },
});

export const esTimeout = (err) => err?.code === 'ETIMEDOUT';

/**
 * Texto legible para un error de la API.
 * Timeout y falta de conexión tienen mensaje propio; si el backend respondió,
 * se usa su `detail` o se unen los mensajes de validación.
 */
export const mensajeError = (err, porDefecto = 'Ocurrió un error.') => {
  if (esTimeout(err)) return MENSAJE_TIMEOUT;
  if (!err?.response) return MENSAJE_SIN_CONEXION;
  const data = err.response.data;
  if (!data || typeof data !== 'object') return porDefecto;
  if (data.detail) return data.detail;
  if (Array.isArray(data)) return data.join(' ') || porDefecto;
  return Object.values(data).flat().join(' ') || porDefecto;
};

export default http;
