import axios from 'axios';
import authService from './auth';

const API_URL = 'http://127.0.0.1:8000/api/usuarios/';

// Función auxiliar para obtener los headers con el token
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

const CONTRATOS_URL = 'http://127.0.0.1:8000/api/contratos/';
const contratoService = { 

  getContratos: async () => {
    const response = await axios.get(CONTRATOS_URL , getAuthHeaders());
    return response.data;
  },
};

const ROLES_URL = 'http://127.0.0.1:8000/api/roles/';
const rolService = { 

  getRoles: async () => {
    const response = await axios.get(ROLES_URL , getAuthHeaders());
    return response.data;
  },
};
export { contratoService , rolService};
export default userService;