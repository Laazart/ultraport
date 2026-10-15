import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import authService from '../../services/auth';
import './login.css';

function RestablecerPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token'); 

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  
  const navigate = useNavigate();

  const handleRestablecer = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');

    if (!token) {
      setError('Enlace inválido. Falta el token de seguridad.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }

    setCargando(true);
    
    try {
      const response = await authService.restablecerPassword(token, password);
      setMensaje(response.mensaje);
      setTimeout(() => navigate('/login'), 3000); 
    } catch (err) {
      setError(err.response?.data?.error || 'El enlace es inválido o ha expirado.');
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="login-page-wrapper d-flex vh-100 w-100">
      <div className="left-side d-none d-md-block"></div>

      <div className="right-side d-flex justify-content-center align-items-center flex-fill">
        <div className="login-box w-100 px-4 text-center" style={{ maxWidth: '560px' }}>
          
          <div className="logo-container d-flex align-items-center justify-content-center gap-3 mb-3">
            <div className="logo-icon">
              <div></div>
              <div></div>
            </div>
            <div className="logo-text">ULTRAPORT</div>
          </div>
          
          <p className="subtitle text-white text-center mb-4">
            Cree una nueva contraseña segura.
          </p>

          {error && <div className="alert alert-danger p-2 mb-3">{error}</div>}
          {mensaje && <div className="alert alert-success p-2 mb-3">{mensaje} Redirigiendo...</div>}

          <form onSubmit={handleRestablecer}>
            <div className="mb-3">
              <input 
                type="password" 
                className="form-control form-control-lg"
                placeholder="Nueva contraseña (mín. 8 caracteres)" 
                required 
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={cargando || mensaje}
              />
            </div>
            <div className="mb-3">
              <input 
                type="password" 
                className="form-control form-control-lg"
                placeholder="Confirmar nueva contraseña" 
                required 
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={cargando || mensaje}
              />
            </div>
            
            <button type="submit" className="btn btn-acceder btn-lg mt-2 mb-4" disabled={cargando || mensaje}>
              {cargando ? 'Guardando...' : 'Restablecer Contraseña'}
            </button>
          </form>

          <Link to="/login" className="forgot-password d-block text-white text-center mb-5">
            Cancelar y volver
          </Link>
        </div>
      </div>
    </div>
  );
}

export default RestablecerPassword;