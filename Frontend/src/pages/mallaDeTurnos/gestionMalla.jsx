import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import TextoRol from '../../components/TextoRol';
import horarioService from '../../services/horario';
import '../home/Home.css';
import './gestionMalla.css';

const RUTA_HOME = '/home';

const ETIQUETAS_BLOQUE = {
  primer_turno: '1° turno (08:00–13:00)',
  segundo_turno: '2° turno (14:00–22:00)',
  tercer_turno: '3° turno (23:00–07:00)',
};

const ORDEN_BLOQUE = { primer_turno: 1, segundo_turno: 2, tercer_turno: 3 };

const agruparPor = (lista, clave) =>
  lista.reduce((acc, item) => {
    const k = clave(item);
    (acc[k] ||= []).push(item);
    return acc;
  }, {});

const GestionMalla = () => {
  const [usuario, setUsuario] = useState(null);
  const [mallas, setMallas] = useState([]);
  const [malla, setMalla] = useState(null);
  const [fecha, setFecha] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    setUsuario(currentUser);
    horarioService
      .listarMallas()
      .then(setMallas)
      .catch(() => setError('No se pudieron cargar las mallas.'));
  }, [navigate]);

  const extraerError = (err) => {
    const data = err.response?.data;
    if (!data) return 'Error de conexión.';
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data)) return data.join(' ');
    return Object.values(data).flat().join(' ');
  };

  const ejecutar = async (fn) => {
    setError('');
    setCargando(true);
    try {
      await fn();
    } catch (err) {
      setError(extraerError(err));
    } finally {
      setCargando(false);
    }
  };

  const seleccionarMalla = (id) =>
    ejecutar(async () => setMalla(await horarioService.obtenerMalla(id)));

  const handleIniciarPlantilla = () =>
    ejecutar(async () => {
      const nueva = await horarioService.iniciarDesdePlantilla(fecha);
      setMalla(nueva);
      setMallas((prev) => [nueva, ...prev]);
    });

  const handleAutocompletar = () =>
    ejecutar(async () => {
      await horarioService.autocompletarMalla(malla.id_malla);
      setMalla(await horarioService.obtenerMalla(malla.id_malla));
    });

  const handlePublicar = () =>
    ejecutar(async () => setMalla(await horarioService.publicarMalla(malla.id_malla)));

  const handleQuitar = (idAsignacion) =>
    ejecutar(async () => {
      await horarioService.quitarAsignacion(idAsignacion);
      setMalla(await horarioService.obtenerMalla(malla.id_malla));
    });

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const editable = malla && malla.estado !== 'publicada' && !cargando;

  const porArea = malla ? agruparPor(malla.turnos, (t) => t.area) : {};

  return (
    <div className="up-shell">
      <div className="up-topbar">
        <div className="up-brand">
          <img src="/logo/logo-ultraport-color.svg" alt="Ultraport" className="up-logo" />
          <span className="sub">Panel de Turnos<TextoRol /></span>
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
        <button onClick={() => navigate(RUTA_HOME)} className="up-back">
          <i className="bi bi-arrow-left"></i>
          Volver
        </button>
      </div>

      <div className="up-hero">
        <h1>Gestión de Malla de Turnos</h1>
      </div>

      {error && <div className="gm-error">{error}</div>}

      <section className="gm-section">
        <h2>Nueva planificación</h2>
        <div className="gm-row">
          <input
            type="date"
            className="gm-input"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
          <button className="gm-btn gm-btn-primary" onClick={handleIniciarPlantilla} disabled={cargando}>
            <i className="bi bi-plus-circle"></i> Iniciar planificación
          </button>
        </div>
      </section>

      <section className="gm-section">
        <h2>Mallas existentes</h2>
        <ul className="gm-lista-mallas">
          {mallas.map((m) => (
            <li key={m.id_malla}>
              <button className="gm-btn" onClick={() => seleccionarMalla(m.id_malla)}>
                {m.fecha} <span className="gm-estado">{m.estado}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {malla && (
        <section className="gm-section">
          <div className="gm-row" style={{ justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ margin: 0 }}>
              Malla del {malla.fecha} <span className="gm-estado">{malla.estado}</span>
            </h2>
            <div className="gm-row">
              <button className="gm-btn" disabled={!editable} onClick={handleAutocompletar}>
                <i className="bi bi-magic"></i> Autocompletar
              </button>
              <button className="gm-btn gm-btn-primary" disabled={!editable} onClick={handlePublicar}>
                <i className="bi bi-send"></i> Publicar
              </button>
            </div>
          </div>

          {Object.entries(porArea).map(([area, turnosArea]) => {
            const porBloque = agruparPor(turnosArea, (t) => t.bloque.nombre_bloque);
            return (
              <div key={area} className="gm-section">
                <h2>{area}</h2>
                {Object.entries(porBloque)
                  .sort(([a], [b]) => ORDEN_BLOQUE[a] - ORDEN_BLOQUE[b])
                  .map(([bloque, turnosBloque]) => (
                    <div key={bloque} className="gm-bloque">
                      <h3 className="gm-bloque-titulo">{ETIQUETAS_BLOQUE[bloque] ?? bloque}</h3>

                      {turnosBloque.map((turno) => (
                        <div key={turno.id_turno} className="gm-turno">
                          <h4 className="gm-turno-titulo">
                            {turno.puesto}
                            <span className="badge-cupos">
                              {turno.asignaciones.length}/{turno.cupos} cupos
                            </span>
                          </h4>

                          {turno.asignaciones.length === 0 ? (
                            <p className="gm-vacio">Sin trabajadores asignados.</p>
                          ) : (
                            <div className="table-responsive">
                              <table className="table gm-tabla">
                                <thead>
                                  <tr>
                                    <th>Nombre</th>
                                    <th>RUT</th>
                                    <th>Correo</th>
                                    <th>Teléfono</th>
                                    <th>Contrato</th>
                                    <th>Máquina</th>
                                    <th>Especialidad</th>
                                    <th>Estado</th>
                                    <th></th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {turno.asignaciones.map((a) => (
                                    <tr key={a.id_asignacion}>
                                      <td>{a.usuario_nombre}</td>
                                      <td>{a.rut ?? '—'}</td>
                                      <td>{a.correo ?? '—'}</td>
                                      <td>{a.telefono ?? '—'}</td>
                                      <td>{a.contrato ?? '—'}</td>
                                      <td>{a.maquina ?? '—'}</td>
                                      <td>{a.especialidad ?? '—'}</td>
                                      <td><span className="gm-estado">{a.estado}</span></td>
                                      <td className="text-end">
                                        {editable && (
                                          <button
                                            className="gm-btn gm-btn-danger"
                                            onClick={() => handleQuitar(a.id_asignacion)}
                                          >
                                            Quitar
                                          </button>
                                        )}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
              </div>
            );
          })}
        </section>
      )}
    </div>
  );
};

export default GestionMalla;