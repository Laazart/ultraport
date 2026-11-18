import authService from './auth';
import http, { API_BASE, TIMEOUT_ARCHIVOS_MS } from './api';

const API_URL = `${API_BASE}inasistencias/`;
const MIS_AVISOS_URL = `${API_URL}mis-avisos/`;

const authHeaders = () => ({
  Authorization: `Bearer ${authService.getAccessToken()}`,
});

const inasistenciasService = {
  listarMios: async () => {
    const response = await http.get(MIS_AVISOS_URL, { headers: authHeaders() });
    return response.data;
  },

  listar: async (estado = '') => {
    const response = await http.get(API_URL, {
      headers: authHeaders(),
      params: estado ? { estado } : {},
    });
    return response.data;
  },

  crear: async ({ motivo, fecha_inicio, fecha_fin, id_turno, adjunto }) => {
    const form = new FormData();
    form.append('motivo', motivo);
    form.append('fecha_inicio', fecha_inicio);
    if (fecha_fin) form.append('fecha_fin', fecha_fin);
    if (id_turno) form.append('id_turno', id_turno);
    if (adjunto) form.append('url_adjunto', adjunto);

    const response = await http.post(MIS_AVISOS_URL, form, {
      headers: authHeaders(),
      timeout: TIMEOUT_ARCHIVOS_MS,
    });
    return response.data;
  },

  cambiarEstado: async (idNotificacion, estado) => {
    const response = await http.patch(
      `${API_URL}${idNotificacion}/estado/`,
      { estado },
      { headers: authHeaders() },
    );
    return response.data;
  },
};

export default inasistenciasService;
