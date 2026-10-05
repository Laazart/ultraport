import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import authService from '../../services/auth'
import './login.css'

function Login() {
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); 
    
    try {  
      await authService.login(correo, password);
      navigate('/home');
    } catch (err) {
      setError('Credenciales incorrectas o problema de conexión.');
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
            Ingrese su correo y contraseña para acceder.
          </p>

          {error && <div className="alert alert-danger p-2 mb-3">{error}</div>}

          <form onSubmit={handleLogin}>
            <div className="mb-3">
              <input 
                type="email" 
                className="form-control form-control-lg"
                placeholder="Correo electronico" 
                required 
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
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

          <a href="#" className="forgot-password d-block text-white text-center mb-5">
            ¿Olvidó su contraseña?
          </a>
        </div>
      </div>
    </div>
  )
}

export default Login