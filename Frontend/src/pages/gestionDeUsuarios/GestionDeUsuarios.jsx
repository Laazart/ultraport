import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import './GestionDeUsuarios.css';
import userService from '../../services/userService';
const RUTA_HOME = '/home';

const GestionDeUsuarios = () => {
  const [usuario, setUsuario] = useState(null);
  const [listaUsuarios, setListaUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [usuarioAEliminar, setUsuarioAEliminar] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      setUsuario(currentUser);
      cargarUsuarios();
    } else {
      navigate('/login');
    }
  }, [navigate]);

  const cargarUsuarios = async () => {
    try {
      setCargando(true);
      const data = await userService.getUsuarios();
      setListaUsuarios(data);
    } catch (error) {
      console.error("Error al cargar los usuarios:", error);
    } finally {
      setCargando(false);
    }
  };

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const handleVolver = () => {
    navigate(RUTA_HOME);
  };
  const handleNuevoUsuario = () => navigate('/usuarios/nuevo');

  // RUTA PARA VER Y OTRA PARA EDITAR
  const handleVerUsuario = (id) => navigate(`/usuarios/ver/${id}`);
  const handleEditarUsuario = (id) => navigate(`/usuarios/editar/${id}`);    

  const abrirModalEliminar = (id) => setUsuarioAEliminar(id);
  const cerrarModalEliminar = () => setUsuarioAEliminar(null);

  const confirmarEliminacion = async () => {
    if (!usuarioAEliminar) return;
    try {
      await userService.eliminarUsuario(usuarioAEliminar);
      setListaUsuarios(listaUsuarios.map(u => 
        u.id_usuario === usuarioAEliminar ? { ...u, estado: 'inactivo' } : u
      ));
    } catch (error) {
      console.error("Error al eliminar el usuario:", error);
      alert("Hubo un error al intentar eliminar el usuario.");
    } finally {
      cerrarModalEliminar();
    }
  };
  return (
    <div className="up-shell">
      <div className="up-topbar">
        <div className="up-brand">
          <img src="/logo/logo-ultraport-color.svg" alt="Ultraport" className="up-logo" />
          <span className="sub">Panel de Turnos{usuario?.rol ? `: ${usuario.rol}` : ''}</span>
        </div>

        <div className="up-user">
          {usuario && (
            <div className="who">
              <div className="name">{usuario.nombres} {usuario.apellidos}</div>
              <div className="rol">{usuario.rut}</div>
            </div>
          )}
          <button onClick={handleLogout} className="up-logout">
            <i className="bi bi-box-arrow-right"></i>
            Cerrar sesión
          </button>
        </div>
      </div>

      <div className="up-subbar">
        <button onClick={handleVolver} className="up-back">
          <i className="bi bi-arrow-left"></i>
          Volver
        </button>
      </div>

      <div className="up-hero mb-4">
        <h1>Gestión de Usuarios</h1>
        <p>Administra los roles, altas y bajas del personal</p>
      </div>
      <div className="up-dashboard-container">
        <div className="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">
          <div className="up-search d-flex align-items-center">
            <i className="bi bi-search me-2"></i>
            <input type="text" placeholder="Buscar por RUT o Nombre..." className="form-control-plaintext" />
          </div>
          <button onClick={handleNuevoUsuario} className="btn-primary d-flex align-items-center gap-2">
            <i className="bi bi-person-plus"></i> Nuevo Usuario
          </button>
        </div>

        <div className="up-table-wrapper">
          <table className="table up-table align-middle mb-0">
            <thead>
              <tr>
                <th>RUT</th>
                <th>Nombre Completo</th>
                <th>Correo</th>
                <th>Telefono</th>
                <th>Estado</th>
                <th className="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cargando ? (
                <tr><td colSpan="5" className="text-center py-4 text-light">Cargando usuarios...</td></tr>
              ) : listaUsuarios.length === 0 ? (
                <tr><td colSpan="5" className="text-center py-4 text-muted">No hay usuarios registrados.</td></tr>
              ) : (
                listaUsuarios.map((u) => (
                  <tr key={u.id_usuario}>
                    <td className="fw-medium text-light">{u.rut}</td>
                    <td className="text-light">{u.nombres} {u.apellidos}</td>
                    <td><span className="rol-text">{u.correo}</span></td>
                    <td><span className="fw-medium ">{u.telefono}</span></td>
                    <td>
                      <span className={`badge rounded-pill up-status-badge ${u.estado === 'activo' ? 'active' : 'inactive'}`}>
                        {u.estado}
                      </span>
                    </td>
                    <td>
                      <div className="d-flex gap-2 justify-content-center">
                        
                        <button onClick={() => handleVerUsuario(u.id_usuario)} className="btn-icon view" title="Ver Detalle">
                          <i className="bi bi-eye"></i>
                        </button>
                        
                        <button 
                          onClick={() => handleEditarUsuario(u.id_usuario)} 
                          className="btn-icon edit" 
                          title="Modificar Usuario">
                          <i className="bi bi-pencil-square"></i>
                        </button>

                        <button 
                          onClick={() => abrirModalEliminar(u.id_usuario)} 
                          className="btn-icon delete" 
                          title="Desactivar"
                          disabled={u.estado === 'inactivo'}
                          style={{ opacity: u.estado === 'inactivo' ? 0.3 : 1, cursor: u.estado === 'inactivo' ? 'not-allowed' : 'pointer' }}>
                          <i className="bi bi-trash"></i>
                        </button>

                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {usuarioAEliminar && (
        <div className="up-modal-overlay">
          <div className="up-modal">
            <div className="up-modal-icon text-danger mb-3">
              <i className="bi bi-exclamation-triangle" style={{fontSize: '40px'}}></i>
            </div>
            <h4 className="text-light mb-2">¿Dar de baja al Usuario?</h4>
            <p className="text-muted mb-4">El usuario pasará a estado inactivo y no podrá acceder al sistema.</p>
            <div className="d-flex gap-3 justify-content-center">
              <button onClick={cerrarModalEliminar} className="btn-secondary">Cancelar</button>
              <button onClick={confirmarEliminacion} className="btn-danger">Sí, desactivar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GestionDeUsuarios;