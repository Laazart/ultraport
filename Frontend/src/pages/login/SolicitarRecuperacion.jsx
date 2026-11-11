import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import authService from '../../services/auth';
import './login.css'; 

function SolicitarRecuperacion() {
  const [identificador, setIdentificador] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  
  const navigate = useNavigate();

  const handleSolicitar = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');
    setCargando(true);
    
    try {
      const response = await authService.solicitarRecuperacion(identificador);
      setMensaje(response.mensaje);
    } catch (err) {
      setError(err.response?.data?.error || 'Ocurrió un error al procesar la solicitud.');
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
            Ingrese su RUT o correo electrónico para recibir un enlace de recuperación.
          </p>

          {error && <div className="alert alert-danger p-2 mb-3">{error}</div>}
          {mensaje && <div className="alert alert-success p-2 mb-3">{mensaje}</div>}

          <form onSubmit={handleSolicitar}>
            <div className="mb-3">
              <input 
                type="text" 
                className="form-control form-control-lg"
                placeholder="RUT o correo electrónico" 
                required 
                value={identificador}
                onChange={(e) => setIdentificador(e.target.value)}
                disabled={cargando}
              />
            </div>
            
            <button type="submit" className="btn btn-acceder btn-lg mt-2 mb-4" disabled={cargando}>
              {cargando ? 'Enviando...' : 'Enviar enlace'}
            </button>
          </form>

          <Link to="/login" className="forgot-password d-block text-white text-center mb-5">
            Volver al inicio de sesión
          </Link>
        </div>
      </div>
    </div>
  );
}

export default SolicitarRecuperacion;