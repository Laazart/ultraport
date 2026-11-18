import authService from './auth';
import http, { API_BASE } from './api';

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
  // Listado paginado (20 por página). Devuelve
  // { count, next, previous, results, pagina, total_paginas }.
  // `busqueda` filtra en el servidor por nombre completo o RUT.
  getUsuarios: async ({ pagina = 1, busqueda = '' } = {}) => {
    const params = { page: pagina };
    if (busqueda.trim()) params.search = busqueda.trim();
    const response = await http.get(API_URL, { ...getAuthHeaders(), params });
    return response.data;
  },

  // Obtener un usuario por su ID
  getUsuarioById: async (id) => {
    const response = await http.get(`${API_URL}${id}/`, getAuthHeaders());
    return response.data;
  },

  // Crear un nuevo usuario (POST)
  crearUsuario: async (usuarioData) => {
    const response = await http.post(API_URL, usuarioData, getAuthHeaders());
    return response.data;
  },

  // Actualizar un usuario existente (PUT o PATCH)
  actualizarUsuario: async (id, usuarioData) => {
    // Usamos PATCH por si no enviamos todos los datos (ej: el password vacío)
    const response = await http.patch(`${API_URL}${id}/`, usuarioData, getAuthHeaders());
    return response.data;
  },

  // Eliminar usuario (Soft delete del backend)
  eliminarUsuario: async (id) => {
    const response = await http.delete(`${API_URL}${id}/`, getAuthHeaders());
    return response.data;
  }
};

const CONTRATOS_URL = `${API_BASE}contratos/`;
const contratoService = { 

  getContratos: async () => {
    const response = await http.get(CONTRATOS_URL , getAuthHeaders());
    return response.data;
  },
};

const ROLES_URL = `${API_BASE}roles/`;
const rolService = { 

  getRoles: async () => {
    const response = await http.get(ROLES_URL , getAuthHeaders());
    return response.data;
  },
};
export { contratoService , rolService};
export default userService;