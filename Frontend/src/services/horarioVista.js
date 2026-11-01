import axios from 'axios';
import authService from './auth';

const API_URL = 'http://127.0.0.1:8000/api/horario/';

const authHeaders = () => ({
  Authorization: `Bearer ${authService.getAccessToken()}`,
});

const horarioVistaService = {
  obtenerDia: async (fecha) => {
    const response = await axios.get(`${API_URL}dia/`, {
      headers: authHeaders(),
      params: fecha ? { fecha } : {},
    });
    return response.data;
  },
};

export default horarioVistaService;
