import axios from 'axios';
import { API_BASE } from './api';

const API_URL = API_BASE;

const authService = {
  login: async (correo, password) => {
    try {
      const response = await axios.post(`${API_URL}login/`, { correo, password });
      
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('usuario', JSON.stringify(response.data.usuario));

      return response.data.usuario;
    } catch (error) {
      console.error("Error en login:", error.response?.data);
      throw error;
    }
  },

  logout: async () => {
    try {
      const refresh = localStorage.getItem('refresh_token');
      const access = localStorage.getItem('access_token');

      if (refresh && access) {
        await axios.post(`${API_URL}logout/`, 
          { refresh }, 
          {
            headers: {
              'Authorization': `Bearer ${access}`,
            }
          }
        );
      }
    } catch (error) {
      console.error("Error al cerrar sesión en el servidor", error.response?.data);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('usuario');
    }
  },

  getAccessToken: () => {
    return localStorage.getItem('access_token');
  },

  getCurrentUser: () => {
    const userStr = localStorage.getItem('usuario');
    if (userStr) return JSON.parse(userStr);
    return null;
  },
  solicitarRecuperacion: async (correo) => {
    const response = await axios.post(`${API_URL}recuperar-password/`, { correo });
    return response.data;
  },
  restablecerPassword: async (token, password) => {
    const response = await axios.post(`${API_URL}restablecer-password/`, { token, password });
    return response.data;
  },
};

export default authService;