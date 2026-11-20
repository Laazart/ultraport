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
// Contrato, puestos, licencias y maquinaria certificada de un usuario.
// guardarCompetencias reemplaza las listas enviadas y devuelve { ..., advertencias }.
const competenciaService = {
  getCompetencias: async (id) => {
    const response = await http.get(`${API_URL}${id}/competencias/`, getAuthHeaders());
    return response.data;
  },

  guardarCompetencias: async (id, datos) => {
    const response = await http.put(`${API_URL}${id}/competencias/`, datos, getAuthHeaders());
    return response.data;
  },
};

const comoLista = (data) => (Array.isArray(data) ? data : data?.results ?? []);

// Catálogos para los selects de competencias.
const catalogoService = {
  getPuestos: async () => comoLista((await http.get(`${API_BASE}puestos/`, getAuthHeaders())).data),
  getTiposLicencia: async () => comoLista((await http.get(`${API_BASE}tipos-licencia/`, getAuthHeaders())).data),
  getMaquinarias: async () => comoLista((await http.get(`${API_BASE}maquinarias/`, getAuthHeaders())).data),
};

const TIPOS_CONTRATO = { bono_turno: 'Bono turno', cppt: 'CPPT', eventual: 'Eventual' };

// Texto legible de un contrato: "CPPT · 4x3 (#3)".
export const etiquetaContrato = (contrato) => {
  const tipo = TIPOS_CONTRATO[contrato.tipo] ?? contrato.tipo;
  const modalidad = contrato.modalidad ? ` · ${contrato.modalidad}` : '';
  return `${tipo}${modalidad} (#${contrato.id_contrato})`;
};

// Une en un texto los mensajes de un error de validación de DRF, incluidos
// los de listas anidadas ({ licencias: [{ fecha_vencimiento: [...] }] }).
export const aplanarErrores = (data) => {
  if (data == null) return [];
  if (typeof data === 'string') return [data];
  if (Array.isArray(data)) return data.flatMap(aplanarErrores);
  if (typeof data === 'object') return Object.values(data).flatMap(aplanarErrores);
  return [String(data)];
};

export { contratoService , rolService, competenciaService, catalogoService };
export default userService;