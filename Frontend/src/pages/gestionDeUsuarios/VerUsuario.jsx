import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import userService, { contratoService , rolService } from '../../services/userService';
import './GestionDeUsuarios.css'; 

const VerUsuario = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [contratos, setContratos] = useState([]);
  const [roles, setRoles] = useState([]);
  const [usuarioData, setUsuarioData] = useState(null);
  const [error, setError] = useState(null);

  const [cargando, setCargando] = useState(true);
  useEffect(() => {
    cargarDatosUsuario(id);
  }, [id]);

  const cargarDatosUsuario = async (userId) => {
    try {
      setCargando(true);
      const data = await userService.getUsuarioById(userId);
      setUsuarioData(data);

      const respuesta = await contratoService.getContratos();
      const lista = Array.isArray(respuesta) ? respuesta : respuesta.results ?? [];
      setContratos(lista);

      const respuestaRoles = await rolService.getRoles();
      const listaRoles = Array.isArray(respuestaRoles)
        ? respuestaRoles
        : respuestaRoles.results ?? [];
      setRoles(listaRoles);
    } catch (error) {
      setError("No se pudo cargar la información del usuario.");
    } finally {
      setCargando(false);
    }
  };

  const contratoAsignado = contratos.find(
  (contrato) =>
    String(contrato.id_contrato) === String(usuarioData.id_contrato)
  );

const obtenerNombreRol = (idRol) => {
  const rol = roles.find(
    (rol) => Number(rol.id_rol) === Number(idRol)
  );
  return rol?.nombre_rol ?? 'Rol no asignado';
};
  
  // Estilos centralizados para mejorar la visibilidad en modo oscuro
  const labelStyle = {
    fontSize: '13px', 
    textTransform: 'uppercase', 
    letterSpacing: '0.05em',
    color: '#A0B2C6', // Color mucho más claro para que resalte
    fontWeight: '600',
    marginBottom: '8px',
    display: 'block'
  };
  const valueBoxStyle = {
    backgroundColor: 'rgba(10, 20, 32, 0.5)', 
    border: '1px solid #1E3349', 
    borderRadius: '8px',
    padding: '14px 16px',
    color: '#E9EEF5', // Texto principal en blanco/gris muy claro
    fontSize: '15px'
  };
  return (
    <div className="up-shell">
      <div className="up-topbar">
        <div className="up-brand">
          <img src="/logo/logo-ultraport-color.svg" alt="Ultraport" className="up-logo" />
          <span className="sub">Panel de Turnos</span>
        </div>
      </div>
      <div className="up-subbar">
        <button onClick={() => navigate('/usuarios')} className="up-back">
          <i className="bi bi-arrow-left"></i> Volver a Usuarios
        </button>
      </div>
      <div className="up-hero mb-4">
        <h1>Detalles del Usuario </h1>
        <p>Información completa registrada en el sistema</p>
      </div>
      <div className="up-dashboard-container" style={{maxWidth: '800px'}}>
        <div className="up-table-wrapper p-4 p-md-5" style={{textAlign: 'left'}}>
          {error && (
            <div className="alert alert-danger" style={{backgroundColor: 'rgba(226, 87, 76, 0.1)', color: '#F2867D', border: '1px solid #E2574C'}}>
              {error}
            </div>
          )}
          {cargando ? (
            <div className="text-center py-5 text-light">
              <div className="spinner-border text-warning mb-3" role="status"></div>
              <div>Cargando información...</div>
            </div>
          ) : usuarioData && (
            <div>
              <div className="d-flex flex-column flex-md-row align-items-center align-items-md-start gap-4 mb-5 pb-4" style={{borderBottom: '1px solid #1E3349'}}>
                <div 
                  className="d-flex align-items-center justify-content-center flex-shrink-0" 
                  style={{ width: '90px', height: '90px', borderRadius: '50%', backgroundColor: 'rgba(242, 166, 61, 0.1)', color: '#F2A63D', fontSize: '40px' }}
                >
                  <i className="bi bi-person-fill"></i>
                </div>
                <div className="text-center text-md-start">
                  <h3 className="text-light mb-1" style={{fontSize: '24px', fontWeight: 'bold'}}>
                    {usuarioData.nombres} {usuarioData.apellidos}
                  </h3>
                  <p style={{color: '#A0B2C6', fontSize: '16px', margin: 0}}>
                    {obtenerNombreRol(usuarioData.id_rol)}
                  </p>
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label style={labelStyle}>RUT</label>
                  <div style={valueBoxStyle}>{usuarioData.rut}</div>
                </div>
                <div className="col-md-6 mt-3 mt-md-0">
                  <label style={labelStyle}>Correo Electrónico</label>
                  <div style={valueBoxStyle}>{usuarioData.correo}</div>
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label style={labelStyle}>Rol del Sistema</label>
                  <div style={valueBoxStyle}>
                    <i className="bi bi-shield-check me-2 text-warning"></i>
                    {obtenerNombreRol(usuarioData.id_rol)}
                  </div>
                </div>
                <div className="col-md-6 mt-3 mt-md-0">
                  <label style={labelStyle}>Contrato Asignado</label>
                  <div style={valueBoxStyle}>
                    {contratoAsignado ? 
                    (
                      <>
                        <i className="bi bi-file-earmark-text me-2" style={{ color: '#3D8BF2' }}/>  {contratoAsignado.tipo}
                        </>
                    ) : usuarioData.id_contrato ? 
                    (
                      `No se encontró el tipo para el contrato ${usuarioData.id_contrato}`
                    ) : 
                    (
                      <span style={{ color: '#E2574C' }}>
                        <i className="bi bi-exclamation-circle me-2" />
                        Sin contrato asignado
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label style={labelStyle}>Estado de Cuenta</label>
                  <div style={{...valueBoxStyle, minHeight: '52px', display: 'flex', alignItems: 'center'}}>
                    <span className={`badge rounded-pill up-status-badge ${usuarioData.estado === 'activo' ? 'active' : 'inactive'}`}>
                      {usuarioData.estado}
                    </span>
                  </div>
                </div>
                <div className="col-md-6 mt-3 mt-md-0">
                  <label style={labelStyle}>Fecha de Registro</label>
                  <div style={valueBoxStyle}>
                    <i className="bi bi-calendar3 me-2" ></i>
                    {usuarioData.fecha_creacion ? new Date(usuarioData.fecha_creacion).toLocaleDateString('es-CL', {
                      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    }) : 'No disponible'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default VerUsuario;