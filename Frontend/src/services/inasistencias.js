import axios from 'axios';
import authService from './auth';

const API_URL = 'http://127.0.0.1:8000/api/inasistencias/';

const authHeaders = () => ({
  Authorization: `Bearer ${authService.getAccessToken()}`,
});

const inasistenciasService = {
  listar: async (estado = '') => {
    const response = await axios.get(API_URL, {
      headers: authHeaders(),
      params: estado ? { estado } : {},
    });
    return response.data;
  },

  // datos: { motivo, fecha_inicio, fecha_fin, id_turno, adjunto (File) }
  crear: async ({ motivo, fecha_inicio, fecha_fin, id_turno, adjunto }) => {
    const form = new FormData();
    form.append('motivo', motivo);
    form.append('fecha_inicio', fecha_inicio);
    if (fecha_fin) form.append('fecha_fin', fecha_fin);
    if (id_turno) form.append('id_turno', id_turno);
    if (adjunto) form.append('url_adjunto', adjunto);

    const response = await axios.post(API_URL, form, { headers: authHeaders() });
    return response.data;
  },

  cambiarEstado: async (idNotificacion, estado) => {
    const response = await axios.patch(
      `${API_URL}${idNotificacion}/estado/`,
      { estado },
      { headers: authHeaders() },
    );
    return response.data;
  },
};

export default inasistenciasService;
