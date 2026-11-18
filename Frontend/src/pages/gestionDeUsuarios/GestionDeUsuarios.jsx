import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import './GestionDeUsuarios.css';
import userService from '../../services/userService';
import { mensajeError } from '../../services/api';

const RUTA_HOME = '/home';
const ESPERA_BUSQUEDA_MS = 300;

const GestionDeUsuarios = () => {
  const [usuario] = useState(() => authService.getCurrentUser());
  const [listaUsuarios, setListaUsuarios] = useState([]);
  const [totalUsuarios, setTotalUsuarios] = useState(0);
  const [totalPaginas, setTotalPaginas] = useState(1);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [usuarioAEliminar, setUsuarioAEliminar] = useState(null);
  // `busqueda` es lo que se escribe; `busquedaAplicada` lo que se envía al
  // servidor, con una pequeña espera para no pedir una página por tecla.
  const [busqueda, setBusqueda] = useState('');
  const [busquedaAplicada, setBusquedaAplicada] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (!usuario) navigate('/login');
  }, [usuario, navigate]);

  useEffect(() => {
    const termino = busqueda.trim();
    if (termino === busquedaAplicada) return undefined;
    const id = setTimeout(() => {
      setBusquedaAplicada(termino);
      setPagina(1);
    }, ESPERA_BUSQUEDA_MS);
    return () => clearTimeout(id);
  }, [busqueda, busquedaAplicada]);

  useEffect(() => {
    if (!usuario) return undefined;
    // Si llega una respuesta de una página/búsqueda anterior, se descarta.
    let vigente = true;
    const cargar = async () => {
      setCargando(true);
      setError('');
      try {
        const data = await userService.getUsuarios({ pagina, busqueda: busquedaAplicada });
        if (!vigente) return;
        setListaUsuarios(data.results);
        setTotalUsuarios(data.count);
        setTotalPaginas(data.total_paginas);
      } catch (err) {
        if (!vigente) return;
        if (err.response?.status === 404 && pagina > 1) {
          // La página dejó de existir (p. ej. cambió el total): volver a la primera.
          setPagina(1);
          return;
        }
        console.error('Error al cargar los usuarios:', err);
        setError(mensajeError(err, 'No se pudieron cargar los usuarios.'));
        setListaUsuarios([]);
      } finally {
        if (vigente) setCargando(false);
      }
    };
    cargar();
    return () => {
      vigente = false;
    };
  }, [usuario, pagina, busquedaAplicada]);

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
            <input
              type="text"
              placeholder="Buscar por RUT o Nombre..."
              className="form-control-plaintext"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
          </div>
          <button onClick={handleNuevoUsuario} className="btn-primary d-flex align-items-center gap-2">
            <i className="bi bi-person-plus"></i> Nuevo Usuario
          </button>
        </div>

        {error && (
          <div className="alert alert-danger" style={{backgroundColor: 'rgba(226, 87, 76, 0.1)', color: '#F2867D', border: '1px solid #E2574C'}}>
            {error}
          </div>
        )}

        <div className="up-table-wrapper">
          <table className="table up-table align-middle mb-0">
            <thead>
              <tr>
                <th>RUT</th>
                <th>Nombre Completo</th>
                <th>Correo</th>
                <th>Telefono</th>
                <th>Contrato</th>
                <th>Estado</th>
                <th className="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cargando ? (
                <tr><td colSpan="7" className="text-center py-4 text-light">Cargando usuarios...</td></tr>
              ) : listaUsuarios.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-4 text-muted">
                    {busquedaAplicada ? 'No se encontraron usuarios.' : 'No hay usuarios registrados.'}
                  </td>
                </tr>
              ) : (
                listaUsuarios.map((u) => (
                  <tr key={u.id_usuario}>
                    <td className="fw-medium text-light">{u.rut}</td>
                    <td className="text-light">{u.nombres} {u.apellidos}</td>
                    <td><span className="rol-text">{u.correo}</span></td>
                    <td><span className="fw-medium">{u.telefono}</span></td>
                    <td>{u.tipo_contrato || <span className="text-muted">Sin contrato</span>}</td>
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

        {totalUsuarios > 0 && (
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-3 mt-3 text-light">
            <span className="text-muted">
              {totalUsuarios} {totalUsuarios === 1 ? 'usuario' : 'usuarios'}
            </span>
            <div className="d-flex align-items-center gap-3">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setPagina((p) => p - 1)}
                disabled={cargando || pagina <= 1}
              >
                <i className="bi bi-chevron-left"></i> Anterior
              </button>
              <span aria-live="polite">Página {pagina} de {totalPaginas}</span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setPagina((p) => p + 1)}
                disabled={cargando || pagina >= totalPaginas}
              >
                Siguiente <i className="bi bi-chevron-right"></i>
              </button>
            </div>
          </div>
        )}
      </div>

      {usuarioAEliminar && (
        <div className="up-modal-overlay">
          <div className="up-modal">
            <div className="up-modal-icon text-danger mb-3">
              <i className="bi bi-exclamation-triangle" style={{ fontSize: '40px' }}></i>
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