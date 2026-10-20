import axios from 'axios';
import authService from './auth';

const API_URL = 'http://127.0.0.1:8000/api/';

const getAuthHeaders = () => {
  const token = authService.getAccessToken();
  return {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  };
};

const horarioService = {
  listarMallas: async () => {
    const response = await axios.get(`${API_URL}mallas/`, getAuthHeaders());
    return response.data;
  },

  obtenerMalla: async (id) => {
    const response = await axios.get(`${API_URL}mallas/${id}/`, getAuthHeaders());
    return response.data;
  },

  iniciarMalla: async (fecha, requerimientos) => {
    const body = { requerimientos };
    if (fecha) body.fecha = fecha;
    const response = await axios.post(`${API_URL}mallas/iniciar/`, body, getAuthHeaders());
    return response.data;
  },

  autocompletarMalla: async (id) => {
    const response = await axios.post(`${API_URL}mallas/${id}/autocompletar/`, {}, getAuthHeaders());
    return response.data;
  },

  publicarMalla: async (id) => {
    const response = await axios.post(`${API_URL}mallas/${id}/publicar/`, {}, getAuthHeaders());
    return response.data;
  },

  candidatosTurno: async (idTurno) => {
    const response = await axios.get(`${API_URL}turnos/${idTurno}/candidatos/`, getAuthHeaders());
    return response.data;
  },

  asignar: async (idTurno, idUsuario) => {
    const response = await axios.post(
      `${API_URL}asignaciones/`,
      { id_turno: idTurno, id_usuario: idUsuario },
      getAuthHeaders()
    );
    return response.data;
  },

  quitarAsignacion: async (idAsignacion) => {
    const response = await axios.delete(`${API_URL}asignaciones/${idAsignacion}/`, getAuthHeaders());
    return response.data;
  },

  reemplazarAsignacion: async (idAsignacion, idUsuario) => {
    const response = await axios.post(
      `${API_URL}asignaciones/${idAsignacion}/reemplazar/`,
      { id_usuario: idUsuario },
      getAuthHeaders()
    );
    return response.data;
  },
    iniciarDesdePlantilla: async (fecha, idBloque = 1) => {
    const body = { id_bloque: idBloque };
    if (fecha) body.fecha = fecha;
    const response = await axios.post(`${API_URL}mallas/iniciar-plantilla/`, body, getAuthHeaders());
    return response.data;
  },
};

export default horarioService;