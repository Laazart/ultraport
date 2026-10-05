import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import './Home.css';

const MODULOS = [
  {
    id: 'notificaciones',
    icon: 'bi-calendar-x',
    titulo: 'Notificar Inasistencia',
    desc: 'Registrar aviso de no disponibilidad',
    ruta: '/notificaciones',
  },
  {
    id: 'malla',
    icon: 'bi-grid-3x3-gap',
    titulo: 'Malla de Turnos',
    desc: 'Ver y generar la cuadrilla del día',
    ruta: '/malla',
  },
  {
    id: 'usuarios',
    icon: 'bi-people',
    titulo: 'Gestión de Usuarios',
    desc: 'Altas, bajas y roles del personal',
    ruta: '/usuarios',
  },
  {
    id: 'reportes',
    icon: 'bi-file-earmark-bar-graph',
    titulo: 'Reportes y Exportación',
    desc: 'Ausentismo y mallas históricas',
    ruta: '/reportes',
  },
];

const obtenerRol = (u) => {
  if (!u) return '';
  if (typeof u.rol === 'string') return u.rol;
  return u.rol?.nombre_rol || u.rol_nombre || u.nombre_rol || '';
};

const Home = () => {
  const [usuario, setUsuario] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      setUsuario(currentUser);
    } else {
      navigate('/login');
    }
  }, [navigate]);

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const handleModuloClick = (modulo) => {
    navigate(modulo.ruta);
  };

  const rol = obtenerRol(usuario);

  return (
    <div className="up-shell">
      <div className="up-topbar">
        <div className="up-brand">
          <img src="/logo/logo-ultraport-color.svg" alt="Ultraport" className="up-logo" />
          <span className="sub">Panel de Turnos{rol ? `: ${rol}` : ''}</span>
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

      <div className="up-hero">
        <h1>{usuario ? `Hola, ${usuario.nombres}` : 'Panel Principal'}</h1>
        <p>Selecciona un módulo para continuar</p>
      </div>

      <div className="up-grid">
        {MODULOS.map((m) => (
          <div
            key={m.id}
            className="up-card"
            role="button"
            tabIndex={0}
            onClick={() => handleModuloClick(m)}
            onKeyDown={(e) => e.key === 'Enter' && handleModuloClick(m)}
          >
            <div className="icon">
              <i className={`bi ${m.icon}`}></i>
            </div>
            <div className="titulo">{m.titulo}</div>
            <div className="desc">{m.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Home;