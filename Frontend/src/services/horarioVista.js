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

  // Semana (lunes a domingo) que contiene `desde`; el backend normaliza al lunes.
  obtenerSemana: async (desde) => {
    const response = await http.get(`${API_URL}semana/`, {
      headers: authHeaders(),
      params: desde ? { desde } : {},
    });
    return response.data;
  },
};

export default horarioVistaService;
