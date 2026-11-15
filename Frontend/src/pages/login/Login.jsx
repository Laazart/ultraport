import { useState } from 'react'
import authService from '../../services/auth'
import './login.css'
import { useNavigate,Link } from 'react-router-dom'

function Login() {
  const [identificador, setIdentificador] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); 
    
    try {  
      await authService.login(identificador, password);
      navigate('/home');
    } catch (err) {
      setError(
        err.response
          ? 'RUT o contraseña incorrectos'
          : 'No se pudo conectar con el servidor.'
      );
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
            Ingrese su RUT o correo y su contraseña para acceder.
          </p>

          {error && <div className="alert alert-danger p-2 mb-3">{error}</div>}

          <form onSubmit={handleLogin}>
            <div className="mb-3">
              <input 
                type="text"
                className="form-control form-control-lg"
                placeholder="RUT o correo electrónico"
                autoComplete="username"
                required
                value={identificador}
                onChange={(e) => setIdentificador(e.target.value)}
              />
            </div>
            <div className="mb-3">
              <input 
                type="password" 
                className="form-control form-control-lg"
                placeholder="Contraseña" 
                required 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            
            <button type="submit" className="btn btn-acceder btn-lg mt-2 mb-4">
              Acceder
            </button>
          </form>

          <Link to="/olvide-contrasena" className="forgot-password d-block text-white text-center mb-5">
            ¿Olvidó su contraseña?
          </Link>
        </div>
      </div>
    </div>
  )
}

export default Login