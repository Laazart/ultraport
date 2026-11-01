import authService from '../services/auth';

const TextoRol = () => {
  const rol = authService.getCurrentUser()?.rol;
  return rol ? `: ${rol}` : null;
};

export default TextoRol;
