import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import TextoRol from '../../components/TextoRol';
import horarioService from '../../services/horario';
import '../home/Home.css';
import './gestionMalla.css';

const RUTA_HOME = '/home';

const ETIQUETAS_BLOQUE = {
  primer_turno: { orden: 1, horario: '08:00 – 13:00' },
  segundo_turno: { orden: 2, horario: '14:00 – 22:00' },
  tercer_turno: { orden: 3, horario: '23:00 – 07:00 (+1 día)' },
};

const ETIQUETAS_ESTADO = {
  borrador: 'Borrador',
  publicada: 'Publicada',
  confirmado: 'Confirmado',
  rechazado: 'Rechazado',
  reemplazado: 'Reemplazado',
};

const agruparPor = (lista, clave) =>
  lista.reduce((acc, item) => {
    const k = clave(item);
    (acc[k] ||= []).push(item);
    return acc;
  }, {});

const formatearFecha = (iso) => {
  const [a, m, d] = iso.split('-');
  return `${d}-${m}-${a}`;
};

const mensajeError = (err) => {
  const data = err.response?.data;
  if (!data) return 'Error de conexión.';
  if (data.detail) return data.detail;
  if (Array.isArray(data)) return data.join(' ');
  return Object.values(data).flat().join(' ') || 'Ocurrió un error.';
};

const bloqueInicialDe = (m) => {
  const con = m.turnos.find((t) => t.asignaciones.length < t.cupos);
  return (con ?? m.turnos[0])?.bloque.nombre_bloque ?? 'primer_turno';
};

const EstadoBadge = ({ estado }) => (
  <span className={`gm-badge gm-badge-${estado}`}>{ETIQUETAS_ESTADO[estado] ?? estado}</span>
);

const EstadoVacio = ({ icono, texto }) => (
  <div className="gm-vacio-bloque">
    <i className={`bi ${icono}`}></i>
    <p>{texto}</p>
  </div>
);

const GestionMalla = () => {
  const [usuario, setUsuario] = useState(null);
  const [mallas, setMallas] = useState([]);
  const [cargandoMallas, setCargandoMallas] = useState(true);
  const [malla, setMalla] = useState(null);
  const [fecha, setFecha] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const [bloqueActivo, setBloqueActivo] = useState('primer_turno');
  const [turnoSeleccionado, setTurnoSeleccionado] = useState(null);
  const [candidatos, setCandidatos] = useState([]);
  const [cargandoCandidatos, setCargandoCandidatos] = useState(false);
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
      .catch(() => setError('No se pudieron cargar las mallas.'))
      .finally(() => setCargandoMallas(false));
  }, [navigate]);

  const ejecutar = async (fn) => {
    setError('');
    setCargando(true);
    try {
      await fn();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  };

  const abrirMalla = (m) => {
    setMalla(m);
    setBloqueActivo(bloqueInicialDe(m));
    setTurnoSeleccionado(null);
    setCandidatos([]);
  };

  const seleccionarMalla = (id) =>
    ejecutar(async () => abrirMalla(await horarioService.obtenerMalla(id)));

  const handleIniciarPlantilla = () =>
    ejecutar(async () => {
      const nueva = await horarioService.iniciarDesdePlantilla(fecha);
      abrirMalla(nueva);
      setMallas((prev) => [nueva, ...prev]);
    });

  const handleAutocompletar = () =>
    ejecutar(async () => {
      await horarioService.autocompletarMalla(malla.id_malla);
      abrirMalla(await horarioService.obtenerMalla(malla.id_malla));
    });

  const handlePublicar = () =>
    ejecutar(async () => abrirMalla(await horarioService.publicarMalla(malla.id_malla)));

  const handleQuitar = (idAsignacion) =>
    ejecutar(async () => {
      await horarioService.quitarAsignacion(idAsignacion);
      const actualizada = await horarioService.obtenerMalla(malla.id_malla);
      setMalla(actualizada);
      if (turnoSeleccionado) {
        const t = actualizada.turnos.find((x) => x.id_turno === turnoSeleccionado.id_turno);
        setTurnoSeleccionado(t ?? null);
      }
    });

  const seleccionarTurno = async (turno) => {
    setTurnoSeleccionado(turno);
    setCargandoCandidatos(true);
    try {
      setCandidatos(await horarioService.candidatosTurno(turno.id_turno));
    } catch (err) {
      setError(mensajeError(err));
      setCandidatos([]);
    } finally {
      setCargandoCandidatos(false);
    }
  };

  const handleAsignar = (idUsuario) =>
    ejecutar(async () => {
      const idTurno = turnoSeleccionado.id_turno;
      await horarioService.asignar(idTurno, idUsuario);
      const actualizada = await horarioService.obtenerMalla(malla.id_malla);
      setMalla(actualizada);
      setTurnoSeleccionado(actualizada.turnos.find((t) => t.id_turno === idTurno) ?? null);
      setCandidatos(await horarioService.candidatosTurno(idTurno));
    });

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const editable = malla && malla.estado !== 'publicada' && !cargando;

  const bloquesPresentes = malla
    ? Object.keys(agruparPor(malla.turnos, (t) => t.bloque.nombre_bloque)).sort(
        (a, b) => ETIQUETAS_BLOQUE[a].orden - ETIQUETAS_BLOQUE[b].orden
      )
    : [];

  const turnosDelBloque = malla
    ? malla.turnos.filter((t) => t.bloque.nombre_bloque === bloqueActivo)
    : [];

  const porArea = agruparPor(turnosDelBloque, (t) => t.area);

  const totalAsignados = malla ? malla.turnos.reduce((n, t) => n + t.asignaciones.length, 0) : 0;
  const totalCupos = malla ? malla.turnos.reduce((n, t) => n + t.cupos, 0) : 0;

  const turnoLleno =
    turnoSeleccionado && turnoSeleccionado.asignaciones.length >= turnoSeleccionado.cupos;

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
        <p>Planifica, asigna y publica la dotación por turno</p>
      </div>

      <div className="gm-contenedor">
        {error && (
          <div className="gm-alerta">
            <i className="bi bi-exclamation-octagon"></i> {error}
          </div>
        )}

        <section className="gm-panel">
          <div className="gm-panel-titulo">
            <i className="bi bi-calendar-plus"></i> Nueva planificación
          </div>
          <div className="gm-row">
            <input
              type="date"
              className="gm-input"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
            <button
              className="gm-btn gm-btn-primario"
              onClick={handleIniciarPlantilla}
              disabled={cargando}
            >
              <i className="bi bi-plus-circle"></i> Iniciar planificación
            </button>
          </div>
        </section>

        <section className="gm-panel">
          <div className="gm-panel-titulo">
            <i className="bi bi-list-ul"></i> Mallas existentes
          </div>

          {cargandoMallas ? (
            <div className="gm-cargando">
              <span className="gm-spinner"></span> Cargando mallas...
            </div>
          ) : mallas.length === 0 ? (
            <p className="gm-muted">Aún no hay mallas creadas.</p>
          ) : (
            <div className="gm-lista-mallas">
              {mallas.map((m) => (
                <button
                  key={m.id_malla}
                  className={`gm-malla-item ${malla?.id_malla === m.id_malla ? 'activa' : ''}`}
                  onClick={() => seleccionarMalla(m.id_malla)}
                >
                  <span>{formatearFecha(m.fecha)}</span>
                  <EstadoBadge estado={m.estado} />
                </button>
              ))}
            </div>
          )}
        </section>

        {malla && (
          <div className="gm-layout">
            <section className="gm-panel gm-principal">
              <div className="gm-cabecera-malla">
                <div>
                  <div className="gm-malla-titulo">
                    Malla del {formatearFecha(malla.fecha)} <EstadoBadge estado={malla.estado} />
                  </div>
                  <div className="gm-malla-sub">
                    {totalAsignados} de {totalCupos} cupos cubiertos
                  </div>
                </div>
                <div className="gm-acciones">
                  <button className="gm-btn" disabled={!editable} onClick={handleAutocompletar}>
                    <i className="bi bi-magic"></i> Autocompletar
                  </button>
                  <button className="gm-btn gm-btn-primario" disabled={!editable} onClick={handlePublicar}>
                    <i className="bi bi-send"></i> Publicar
                  </button>
                </div>
              </div>

              <div className="gm-tabs" role="tablist">
                {bloquesPresentes.map((b) => {
                  const total = malla.turnos
                    .filter((t) => t.bloque.nombre_bloque === b)
                    .reduce((n, t) => n + t.asignaciones.length, 0);
                  return (
                    <button
                      key={b}
                      type="button"
                      role="tab"
                      aria-selected={b === bloqueActivo}
                      className={`gm-tab ${b === bloqueActivo ? 'activo' : ''}`}
                      onClick={() => setBloqueActivo(b)}
                    >
                      <span className="gm-tab-nombre">{ETIQUETAS_BLOQUE[b].orden}° turno</span>
                      <span className="gm-tab-horario">{ETIQUETAS_BLOQUE[b].horario}</span>
                      <span className="gm-tab-total">{total}</span>
                    </button>
                  );
                })}
              </div>

              {Object.keys(porArea).length === 0 ? (
                <EstadoVacio icono="bi-people" texto="No hay turnos en este bloque." />
              ) : (
                Object.entries(porArea).map(([area, turnosArea]) => (
                  <div key={area} className="gm-area">
                    <h3 className="gm-area-titulo">{area}</h3>

                    {turnosArea.map((turno) => {
                      const seleccionado = turnoSeleccionado?.id_turno === turno.id_turno;
                      return (
                        <div
                          key={turno.id_turno}
                          className={`gm-turno ${seleccionado ? 'seleccionado' : ''}`}
                          onClick={() => seleccionarTurno(turno)}
                        >
                          <div className="gm-turno-cabecera">
                            <span className="gm-turno-puesto">{turno.puesto}</span>
                            <span
                              className={`gm-cupos ${turno.asignaciones.length >= turno.cupos ? 'completo' : ''}`}
                            >
                              {turno.asignaciones.length}/{turno.cupos}
                            </span>
                          </div>

                          {turno.asignaciones.length === 0 ? (
                            <p className="gm-vacio">Sin trabajadores asignados.</p>
                          ) : (
                            <div className="table-responsive">
                              <table className="gm-tabla">
                                <thead>
                                  <tr>
                                    <th>Nombre</th>
                                    <th>RUT</th>
                                    <th>Correo</th>
                                    <th>Contrato</th>
                                    <th>Máquina</th>
                                    <th>Especialidad</th>
                                    <th>Estado</th>
                                    {editable && <th className="gm-col-acciones"></th>}
                                  </tr>
                                </thead>
                                <tbody>
                                  {turno.asignaciones.map((a) => (
                                    <tr key={a.id_asignacion}>
                                      <td className="gm-nombre">{a.usuario_nombre}</td>
                                      <td className="gm-mono">{a.rut ?? '—'}</td>
                                      <td>{a.correo ?? '—'}</td>
                                      <td>{a.contrato ?? '—'}</td>
                                      <td>{a.maquina ?? '—'}</td>
                                      <td>{a.especialidad ?? '—'}</td>
                                      <td>
                                        <EstadoBadge
                                          estado={malla.estado === 'publicada' ? 'confirmado' : a.estado}
                                        />
                                      </td>
                                      {editable && (
                                        <td className="gm-col-acciones">
                                          <button
                                            className="gm-btn-quitar"
                                            title="Quitar de este turno"
                                            disabled={cargando}
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              handleQuitar(a.id_asignacion);
                                            }}
                                          >
                                            <i className="bi bi-x-lg"></i>
                                          </button>
                                        </td>
                                      )}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </section>

            <aside className="gm-panel gm-candidatos">
              <div className="gm-panel-titulo">
                <i className="bi bi-person-plus"></i> Candidatos disponibles
              </div>

              {!turnoSeleccionado ? (
                <p className="gm-muted">Selecciona un turno para ver quién puede ocupar un cupo.</p>
              ) : (
                <>
                  <div className="gm-candidatos-turno">
                    <strong>{turnoSeleccionado.puesto}</strong>
                    <span>
                      {turnoSeleccionado.area} ·{' '}
                      {ETIQUETAS_BLOQUE[turnoSeleccionado.bloque.nombre_bloque]?.horario}
                    </span>
                    <span className={`gm-cupos ${turnoLleno ? 'completo' : ''}`}>
                      {turnoSeleccionado.asignaciones.length}/{turnoSeleccionado.cupos} cupos
                    </span>
                  </div>

                  {cargandoCandidatos ? (
                    <p className="gm-muted">Buscando candidatos...</p>
                  ) : candidatos.length === 0 ? (
                    <p className="gm-muted">No hay trabajadores aptos para este turno.</p>
                  ) : (
                    <ul className="gm-lista-candidatos">
                      {candidatos.map((c) => (
                        <li key={c.id_usuario}>
                          <div className="gm-candidato-info">
                            <div className="gm-nombre">{c.nombre}</div>
                            <div className="gm-candidato-meta">
                              <span className="gm-mono">{c.rut ?? '—'}</span>
                              <span>{c.correo ?? '—'}</span>
                              <span>{c.telefono ?? 'Sin teléfono'}</span>
                            </div>
                            <div className="gm-candidato-horas">
                              <i className="bi bi-clock"></i> {c.horas_semana} h esta semana
                            </div>
                          </div>
                          <button
                            className="gm-btn gm-btn-primario"
                            disabled={!editable || turnoLleno || cargando}
                            onClick={() => handleAsignar(c.id_usuario)}
                          >
                            Asignar
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </aside>
          </div>
        )}
      </div>
    </div>
  );
};

export default GestionMalla;