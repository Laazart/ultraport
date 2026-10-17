import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import inasistenciasService from '../../services/inasistencias';
import '../home/Home.css';
import './notificarInasistencia.css';

const RUTA_HOME = '/home';
const ROLES_GESTION = ['Encargado de Planificacion', 'Administrador'];

const ESTADOS = [
  { valor: 'pendiente', etiqueta: 'Pendiente' },
  { valor: 'aprobado', etiqueta: 'Aprobado' },
  { valor: 'rechazado', etiqueta: 'Rechazado' },
];

const FORM_INICIAL = { motivo: '', fecha_inicio: '', fecha_fin: '', adjunto: null };

const formatearFecha = (iso) => {
  if (!iso) return '—';
  const [a, m, d] = iso.slice(0, 10).split('-');
  return `${d}-${m}-${a}`;
};

const rangoFechas = (n) =>
  n.fecha_fin && n.fecha_fin !== n.fecha_inicio
    ? `${formatearFecha(n.fecha_inicio)} al ${formatearFecha(n.fecha_fin)}`
    : formatearFecha(n.fecha_inicio);

// Convierte los errores de DRF ({campo: [msg]}) en un solo texto.
const mensajeError = (err, porDefecto) => {
  const data = err.response?.data;
  if (!data) return porDefecto;
  if (data.detail) return data.detail;
  return Object.values(data).flat().join(' ') || porDefecto;
};

const BadgeEstado = ({ estado }) => (
  <span className={`ina-badge ina-badge-${estado}`}>
    {ESTADOS.find((e) => e.valor === estado)?.etiqueta || estado}
  </span>
);

const LinkAdjunto = ({ url }) =>
  url ? (
    <a href={url} target="_blank" rel="noopener noreferrer" className="ina-link">
      <i className="bi bi-paperclip"></i> Ver
    </a>
  ) : (
    <span className="ina-muted">—</span>
  );

/* ---------- Vista del trabajador: formulario + mis avisos ---------- */
const VistaTrabajador = () => {
  const [form, setForm] = useState(FORM_INICIAL);
  const [inputKey, setInputKey] = useState(0);
  const [avisos, setAvisos] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const cargar = useCallback(async () => {
    try {
      setAvisos(await inasistenciasService.listar());
    } catch (err) {
      setError(mensajeError(err, 'No se pudieron cargar tus avisos.'));
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const handleChange = (e) => {
    const { name, value, files } = e.target;
    setForm((f) => ({ ...f, [name]: files ? files[0] || null : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMensaje('');

    if (!form.motivo.trim() || !form.fecha_inicio) {
      setError('Completa el motivo y la fecha de inicio.');
      return;
    }
    if (form.fecha_fin && form.fecha_fin < form.fecha_inicio) {
      setError('La fecha de término no puede ser anterior a la de inicio.');
      return;
    }

    setEnviando(true);
    try {
      await inasistenciasService.crear(form);
      setMensaje('Aviso enviado. Quedó en estado pendiente de revisión.');
      setForm(FORM_INICIAL);
      setInputKey((k) => k + 1); // limpia el input de archivo
      cargar();
    } catch (err) {
      setError(mensajeError(err, 'No se pudo enviar el aviso.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="ina-layout">
      <form className="ina-panel" onSubmit={handleSubmit}>
        <h2 className="ina-panel-titulo">Nuevo aviso</h2>

        {error && <div className="alert alert-danger p-2">{error}</div>}
        {mensaje && <div className="alert alert-success p-2">{mensaje}</div>}

        <label className="ina-label" htmlFor="motivo">Motivo *</label>
        <textarea
          id="motivo"
          name="motivo"
          className="form-control ina-input"
          rows={3}
          maxLength={255}
          placeholder="Ej: licencia médica, trámite personal..."
          value={form.motivo}
          onChange={handleChange}
          disabled={enviando}
          required
        />

        <div className="ina-fila">
          <div>
            <label className="ina-label" htmlFor="fecha_inicio">Fecha inicio *</label>
            <input
              id="fecha_inicio"
              name="fecha_inicio"
              type="date"
              className="form-control ina-input"
              value={form.fecha_inicio}
              onChange={handleChange}
              disabled={enviando}
              required
            />
          </div>
          <div>
            <label className="ina-label" htmlFor="fecha_fin">Fecha término</label>
            <input
              id="fecha_fin"
              name="fecha_fin"
              type="date"
              className="form-control ina-input"
              min={form.fecha_inicio || undefined}
              value={form.fecha_fin}
              onChange={handleChange}
              disabled={enviando}
            />
          </div>
        </div>

        <label className="ina-label" htmlFor="adjunto">Respaldo (JPG, PNG o PDF, máx. 5 MB)</label>
        <input
          key={inputKey}
          id="adjunto"
          name="adjunto"
          type="file"
          accept=".jpg,.jpeg,.png,.pdf"
          className="form-control ina-input"
          onChange={handleChange}
          disabled={enviando}
        />

        <button type="submit" className="ina-btn" disabled={enviando}>
          {enviando ? 'Enviando...' : 'Enviar aviso'}
        </button>
      </form>

      <div className="ina-panel">
        <h2 className="ina-panel-titulo">Mis avisos</h2>
        {avisos.length === 0 ? (
          <p className="ina-muted">Aún no has registrado avisos.</p>
        ) : (
          <ul className="ina-lista">
            {avisos.map((a) => (
              <li key={a.id_notificacion} className="ina-item">
                <div className="ina-item-top">
                  <span className="ina-fechas">{rangoFechas(a)}</span>
                  <BadgeEstado estado={a.estado} />
                </div>
                <div className="ina-motivo">{a.motivo}</div>
                <div className="ina-item-pie">
                  <span>Enviado {formatearFecha(a.fecha_registro)}</span>
                  <LinkAdjunto url={a.url_adjunto} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

/* ---------- Vista del encargado: gestión de tickets ---------- */
const VistaEncargado = () => {
  const [filtro, setFiltro] = useState('pendiente');
  const [avisos, setAvisos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [actualizando, setActualizando] = useState(null);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    setCargando(true);
    setError('');
    try {
      setAvisos(await inasistenciasService.listar(filtro));
    } catch (err) {
      setError(mensajeError(err, 'No se pudieron cargar los avisos.'));
    } finally {
      setCargando(false);
    }
  }, [filtro]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const handleEstado = async (aviso, estado) => {
    if (estado === aviso.estado) return;
    setActualizando(aviso.id_notificacion);
    setError('');
    try {
      const actualizado = await inasistenciasService.cambiarEstado(aviso.id_notificacion, estado);
      setAvisos((lista) =>
        lista
          .map((a) => (a.id_notificacion === actualizado.id_notificacion ? actualizado : a))
          // si hay filtro activo y el aviso ya no calza, se quita de la lista
          .filter((a) => !filtro || a.estado === filtro),
      );
    } catch (err) {
      setError(mensajeError(err, 'No se pudo actualizar el estado.'));
    } finally {
      setActualizando(null);
    }
  };

  return (
    <div className="ina-panel">
      <div className="ina-filtros">
        {[{ valor: '', etiqueta: 'Todos' }, ...ESTADOS].map((e) => (
          <button
            key={e.valor || 'todos'}
            type="button"
            className={`ina-chip ${filtro === e.valor ? 'activo' : ''}`}
            onClick={() => setFiltro(e.valor)}
          >
            {e.etiqueta}
          </button>
        ))}
      </div>

      {error && <div className="alert alert-danger p-2">{error}</div>}

      {cargando ? (
        <p className="ina-muted">Cargando...</p>
      ) : avisos.length === 0 ? (
        <p className="ina-muted">No hay avisos en esta categoría.</p>
      ) : (
        <div className="table-responsive">
          <table className="ina-tabla">
            <thead>
              <tr>
                <th>Trabajador</th>
                <th>Fechas</th>
                <th>Motivo</th>
                <th>Respaldo</th>
                <th>Enviado</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {avisos.map((a) => (
                <tr key={a.id_notificacion}>
                  <td>
                    <div>{a.usuario.nombres} {a.usuario.apellidos}</div>
                    <div className="ina-muted">{a.usuario.rut}</div>
                  </td>
                  <td className="ina-nowrap">{rangoFechas(a)}</td>
                  <td className="ina-motivo">{a.motivo}</td>
                  <td><LinkAdjunto url={a.url_adjunto} /></td>
                  <td className="ina-nowrap">{formatearFecha(a.fecha_registro)}</td>
                  <td><BadgeEstado estado={a.estado} /></td>
                  <td>
                    <div className="ina-acciones">
                      <button
                        type="button"
                        className="ina-accion aprobar"
                        disabled={actualizando === a.id_notificacion || a.estado === 'aprobado'}
                        onClick={() => handleEstado(a, 'aprobado')}
                        title="Aprobar"
                      >
                        <i className="bi bi-check-lg"></i>
                      </button>
                      <button
                        type="button"
                        className="ina-accion rechazar"
                        disabled={actualizando === a.id_notificacion || a.estado === 'rechazado'}
                        onClick={() => handleEstado(a, 'rechazado')}
                        title="Rechazar"
                      >
                        <i className="bi bi-x-lg"></i>
                      </button>
                      <button
                        type="button"
                        className="ina-accion"
                        disabled={actualizando === a.id_notificacion || a.estado === 'pendiente'}
                        onClick={() => handleEstado(a, 'pendiente')}
                        title="Volver a pendiente"
                      >
                        <i className="bi bi-arrow-counterclockwise"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const NotificarInasistencia = () => {
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

  const handleVolver = () => {
    navigate(RUTA_HOME);
  };

  const esEncargado = ROLES_GESTION.includes(usuario?.rol);

  return (
    <div className="up-shell">
      <div className="up-topbar">
        <div className="up-brand">
          <img src="/logo/logo-ultraport-color.svg" alt="Ultraport" className="up-logo" />
          <span className="sub">Panel de Turnos</span>
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

      <div className="up-hero">
        <h1>{esEncargado ? 'Gestión de Avisos de Inasistencia' : 'Notificar Inasistencia'}</h1>
        <p>
          {esEncargado
            ? 'Revisa los avisos enviados y apruébalos o recházalos'
            : 'Informa tu no disponibilidad y revisa el estado de tus avisos'}
        </p>
      </div>

      {usuario && (esEncargado ? <VistaEncargado /> : <VistaTrabajador />)}
    </div>
  );
};

export default NotificarInasistencia;
