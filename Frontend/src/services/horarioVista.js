import authService from './auth';
import http, { API_BASE } from './api';

const API_URL = `${API_BASE}horario/`;
const authHeaders = () => ({
  Authorization: `Bearer ${authService.getAccessToken()}`,
});

const horarioVistaService = {
  obtenerDia: async (fecha) => {
    const response = await http.get(`${API_URL}dia/`, {
      headers: authHeaders(),
      params: fecha ? { fecha } : {},
    });
    return response.data;
  },
};

export default horarioVistaService;
