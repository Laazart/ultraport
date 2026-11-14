import axios from 'axios';
import authService from './auth';
import { API_BASE } from './api';

const API_URL = `${API_BASE}usuarios/`;
const getAuthHeaders = () => {
  const token = authService.getAccessToken();

  return {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  };
};

const userService = {
  // Obtener todos los usuarios
  getUsuarios: async () => {
    const response = await axios.get(API_URL, getAuthHeaders());
    return response.data;
  },

  // Obtener un usuario por su ID
  getUsuarioById: async (id) => {
    const response = await axios.get(`${API_URL}${id}/`, getAuthHeaders());
    return response.data;
  },

  // Crear un nuevo usuario (POST)
  crearUsuario: async (usuarioData) => {
    const response = await axios.post(API_URL, usuarioData, getAuthHeaders());
    return response.data;
  },

  // Actualizar un usuario existente (PUT o PATCH)
  actualizarUsuario: async (id, usuarioData) => {
    // Usamos PATCH por si no enviamos todos los datos (ej: el password vacío)
    const response = await axios.patch(`${API_URL}${id}/`, usuarioData, getAuthHeaders());
    return response.data;
  },

  // Eliminar usuario (Soft delete del backend)
  eliminarUsuario: async (id) => {
    const response = await axios.delete(`${API_URL}${id}/`, getAuthHeaders());
    return response.data;
  }
};

const CONTRATOS_URL = `${API_BASE}contratos/`;
const contratoService = { 

  getContratos: async () => {
    const response = await axios.get(CONTRATOS_URL , getAuthHeaders());
    return response.data;
  },
};

const ROLES_URL = `${API_BASE}roles/`;
const rolService = { 

  getRoles: async () => {
    const response = await axios.get(ROLES_URL , getAuthHeaders());
    return response.data;
  },
};
export { contratoService , rolService};
export default userService;