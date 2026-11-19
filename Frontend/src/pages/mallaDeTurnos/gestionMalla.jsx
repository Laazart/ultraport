import { useEffect, useEffectEvent, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import authService from '../../services/auth';
import TextoRol from '../../components/TextoRol';
import horarioService from '../../services/horario';
import { mensajeError } from '../../services/api';
import BotonCargando from '../../components/BotonCargando';
import '../home/home.css';
import './gestionMalla.css';

const RUTA_HOME = '/home';
const FECHA_ISO = /^\d{4}-\d{2}-\d{2}$/;
const TURNO_POR_DEFECTO = 1;

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

const hhmm = (hora) => (hora ? hora.slice(0, 5) : '');

// Horario del bloque según el API (cruza medianoche si termina antes de empezar).
const horarioBloque = (bloque) => {
  if (!bloque) return '';
  const cruza = bloque.hora_termino <= bloque.hora_inicio;
  return `${hhmm(bloque.hora_inicio)} – ${hhmm(bloque.hora_termino)}${cruza ? ' (+1 día)' : ''}`;
};

const nombreTurno = (bloque) => `${bloque.orden_secuencia}° turno`;

const estadoCupos = (asignados, cupos) => {
  if (asignados > cupos) return 'excedido';
  if (asignados === cupos) return 'completo';
  return '';
};

const bloqueInicialDe = (m) => {
  const con = m.turnos.find((t) => t.asignaciones.length < t.cupos);
  return (con ?? m.turnos[0])?.bloque.nombre_bloque ?? 'primer_turno';
};

// Pestaña (nombre_bloque) del turno N en la malla, o null si no existe.
const bloquePorOrden = (m, orden) =>
  m.turnos.find((t) => t.bloque.orden_secuencia === orden)?.bloque.nombre_bloque ?? null;

const ordenDeBloque = (m, nombreBloque) =>
  m.turnos.find((t) => t.bloque.nombre_bloque === nombreBloque)?.bloque.orden_secuencia ?? null;

// ?turno=N válido (entero positivo) o null.
const leerTurno = (valor) => {
  const n = Number(valor);
  return Number.isInteger(n) && n > 0 ? n : null;
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

// Los cupos son referencia: se muestra "x / y" y un aviso si se exceden.
const Cupos = ({ asignados, cupos, sufijo = '' }) => {
  const estado = estadoCupos(asignados, cupos);
  return (
    <span
      className={`gm-cupos ${estado}`}
      title={estado === 'excedido' ? 'Supera los cupos de referencia' : undefined}
    >
      {estado === 'excedido' && <i className="bi bi-exclamation-triangle"></i>}
      {asignados} / {cupos}
      {sufijo}
    </span>
  );
};

const GestionMalla = () => {
  const [usuario, setUsuario] = useState(null);
  const [mallas, setMallas] = useState([]);
  const [cargandoMallas, setCargandoMallas] = useState(true);
  const [malla, setMalla] = useState(null);
  const [fecha, setFecha] = useState('');
  // Turno (orden_secuencia) elegido en "Nueva planificación".
  const [turnoNuevo, setTurnoNuevo] = useState(TURNO_POR_DEFECTO);
  const [bloquesCatalogo, setBloquesCatalogo] = useState([]);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [cargando, setCargando] = useState(false);
  // Qué botón disparó la operación en curso, para mostrar su spinner.
  const [accion, setAccion] = useState(null);
  const [bloqueActivo, setBloqueActivo] = useState('primer_turno');
  const [turnoSeleccionado, setTurnoSeleccionado] = useState(null);
  const [candidatos, setCandidatos] = useState([]);
  const [cargandoCandidatos, setCargandoCandidatos] = useState(false);
  // Asignación que se está moviendo: { id, destino }.
  const [moviendo, setMoviendo] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const ejecutar = async (fn, clave = null) => {
    setError('');
    setCargando(true);
    setAccion(clave);
    try {
      await fn();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
      setAccion(null);
    }
  };

  // Refleja la malla y el turno abiertos en la URL (?fecha=...&turno=N).
  const sincronizarUrl = (fechaMalla, orden) => {
    const turno = orden ? String(orden) : null;
    if (searchParams.get('fecha') === fechaMalla && searchParams.get('turno') === turno) return;
    setSearchParams(turno ? { fecha: fechaMalla, turno } : { fecha: fechaMalla }, { replace: true });
  };

  // orden: turno a abrir (1, 2, 3). Sin orden, el primer bloque con cupos libres.
  const abrirMalla = (m, orden = null) => {
    const bloque = (orden && bloquePorOrden(m, orden)) || bloqueInicialDe(m);
    setMalla(m);
    setAviso('');
    setBloqueActivo(bloque);
    setTurnoSeleccionado(null);
    setCandidatos([]);
    setMoviendo(null);
    setMallas((prev) => prev.map((x) => (x.id_malla === m.id_malla ? { ...x, estado: m.estado } : x)));
    sincronizarUrl(m.fecha, ordenDeBloque(m, bloque));
  };

  const cambiarBloque = (b) => {
    setBloqueActivo(b.nombre_bloque);
    sincronizarUrl(malla.fecha, b.orden_secuencia);
  };

  const seleccionarMalla = (id, orden = null) =>
    ejecutar(async () => abrirMalla(await horarioService.obtenerMalla(id), orden));

  // ?fecha=YYYY-MM-DD&turno=N (p. ej. desde Visualización de horario) abre la
  // malla de esa fecha en ese turno o, si no existe, deja fecha y turno listos
  // para iniciar la planificación.
  const abrirDesdeEnlace = useEffectEvent((lista) => {
    const fechaEnlace = searchParams.get('fecha');
    const turnoEnlace = leerTurno(searchParams.get('turno'));
    if (turnoEnlace) setTurnoNuevo(turnoEnlace);
    if (!fechaEnlace) return;
    if (!FECHA_ISO.test(fechaEnlace)) {
      setAviso('La fecha indicada en el enlace no es válida (AAAA-MM-DD).');
      return;
    }
    const encontrada = lista.find((m) => m.fecha === fechaEnlace);
    if (encontrada) {
      seleccionarMalla(encontrada.id_malla, turnoEnlace);
    } else {
      setFecha(fechaEnlace);
      setAviso(`No hay malla para el ${formatearFecha(fechaEnlace)}; puedes iniciarla.`);
    }
  });

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    setUsuario(currentUser);
    horarioService
      .listarMallas()
      .then((lista) => {
        setMallas(lista);
        abrirDesdeEnlace(lista);
      })
      .catch((err) => setError(mensajeError(err, 'No se pudieron cargar las mallas.')))
      .finally(() => setCargandoMallas(false));
    horarioService
      .listarBloques()
      .then(setBloquesCatalogo)
      .catch((err) => setError(mensajeError(err, 'No se pudieron cargar los turnos.')));
  }, [navigate]);

  const recargarCandidatos = async (idTurno) => {
    setCargandoCandidatos(true);
    try {
      setCandidatos(await horarioService.candidatosTurno(idTurno));
    } catch (err) {
      setError(mensajeError(err));
      setCandidatos([]);
    } finally {
      setCargandoCandidatos(false);
    }
  };

  // Recarga la malla tras un cambio y mantiene el turno seleccionado y sus candidatos.
  const refrescarMalla = async () => {
    const actualizada = await horarioService.obtenerMalla(malla.id_malla);
    setMalla(actualizada);
    if (turnoSeleccionado) {
      const idTurno = turnoSeleccionado.id_turno;
      setTurnoSeleccionado(actualizada.turnos.find((t) => t.id_turno === idTurno) ?? null);
      await recargarCandidatos(idTurno);
    }
  };

  // Crea la malla del día (3 bloques) y la abre en el turno elegido. Si ya
  // existe una malla para esa fecha, la abre en ese turno en vez de fallar.
  const handleIniciarPlantilla = () =>
    ejecutar(async () => {
      const yaListada = fecha ? mallas.find((m) => m.fecha === fecha) : null;
      const resultado = yaListada
        ? await horarioService.obtenerMalla(yaListada.id_malla)
        : await horarioService.iniciarDesdePlantilla(fecha);
      const existia = Boolean(yaListada) || mallas.some((m) => m.id_malla === resultado.id_malla);
      if (!existia) setMallas((prev) => [resultado, ...prev]);
      abrirMalla(resultado, turnoNuevo);
      if (existia) {
        setAviso(`Ya existía una malla para el ${formatearFecha(resultado.fecha)}; se abrió en el ${turnoNuevo}° turno.`);
      }
    }, 'iniciar');

  const handleAutocompletar = () =>
    ejecutar(async () => {
      await horarioService.autocompletarMalla(malla.id_malla);
      abrirMalla(await horarioService.obtenerMalla(malla.id_malla));
    }, 'autocompletar');

  const handlePublicar = () =>
    ejecutar(async () => abrirMalla(await horarioService.publicarMalla(malla.id_malla)), 'publicar');

  const handleQuitar = (idAsignacion) =>
    ejecutar(async () => {
      await horarioService.quitarAsignacion(idAsignacion);
      await refrescarMalla();
    }, `quitar-${idAsignacion}`);

  const handleAsignar = (idUsuario) =>
    ejecutar(async () => {
      await horarioService.asignar(turnoSeleccionado.id_turno, idUsuario);
      await refrescarMalla();
    }, `asignar-${idUsuario}`);

  const handleMover = () =>
    ejecutar(async () => {
      await horarioService.moverAsignacion(moviendo.id, Number(moviendo.destino));
      setMoviendo(null);
      await refrescarMalla();
    }, `mover-${moviendo.id}`);

  const seleccionarTurno = (turno) => {
    setTurnoSeleccionado(turno);
    recargarCandidatos(turno.id_turno);
  };

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const publicada = malla?.estado === 'publicada';
  const editable = Boolean(malla) && !cargando;

  const bloques = malla
    ? Object.values(
        Object.fromEntries(malla.turnos.map((t) => [t.bloque.nombre_bloque, t.bloque]))
      ).sort((a, b) => a.orden_secuencia - b.orden_secuencia)
    : [];

  const turnosDelBloque = malla
    ? malla.turnos.filter((t) => t.bloque.nombre_bloque === bloqueActivo)
    : [];

  const porArea = agruparPor(turnosDelBloque, (t) => t.area);

  const totalAsignados = malla ? malla.turnos.reduce((n, t) => n + t.asignaciones.length, 0) : 0;
  const totalCupos = malla ? malla.turnos.reduce((n, t) => n + t.cupos, 0) : 0;
  const turnosExcedidos = malla
    ? malla.turnos.filter((t) => t.asignaciones.length > t.cupos).length
    : 0;

  const disponibles = candidatos.filter((c) => c.asignable);
  const noAsignables = candidatos.filter((c) => !c.asignable);

  // Destinos posibles para mover: los demás turnos de la malla, agrupados por bloque.
  const destinosPorBloque = (idTurnoOrigen) =>
    bloques.map((b) => ({
      bloque: b,
      turnos: malla.turnos.filter(
        (t) => t.bloque.nombre_bloque === b.nombre_bloque && t.id_turno !== idTurnoOrigen
      ),
    }));

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
        {aviso && (
          <div className="gm-aviso">
            <i className="bi bi-info-circle"></i> {aviso}
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
              aria-label="Fecha de la malla"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
            <select
              className="gm-input"
              aria-label="Turno a abrir"
              value={turnoNuevo}
              onChange={(e) => setTurnoNuevo(Number(e.target.value))}
              disabled={bloquesCatalogo.length === 0}
            >
              {bloquesCatalogo.length === 0 ? (
                <option value={turnoNuevo}>Cargando turnos...</option>
              ) : (
                bloquesCatalogo.map((b) => (
                  <option key={b.id_bloque} value={b.orden_secuencia}>
                    {nombreTurno(b)} · {horarioBloque(b)}
                  </option>
                ))
              )}
            </select>
            <BotonCargando
              className="gm-btn gm-btn-primario"
              onClick={handleIniciarPlantilla}
              disabled={cargando}
              cargando={accion === 'iniciar'}
              textoCargando="Iniciando..."
            >
              <i className="bi bi-plus-circle"></i> Iniciar planificación
            </BotonCargando>
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
                    {turnosExcedidos > 0 && (
                      <span className="gm-texto-excedido">
                        {' '}· <i className="bi bi-exclamation-triangle"></i> {turnosExcedidos}{' '}
                        turno(s) sobre el cupo
                      </span>
                    )}
                  </div>
                </div>
                <div className="gm-acciones">
                  <BotonCargando
                    className="gm-btn"
                    disabled={!editable}
                    cargando={accion === 'autocompletar'}
                    textoCargando="Autocompletando..."
                    onClick={handleAutocompletar}
                  >
                    <i className="bi bi-magic"></i> Autocompletar
                  </BotonCargando>
                  <BotonCargando
                    className="gm-btn gm-btn-primario"
                    disabled={!editable || publicada}
                    cargando={accion === 'publicar'}
                    textoCargando="Publicando..."
                    onClick={handlePublicar}
                    title={publicada ? 'La malla ya está publicada' : undefined}
                  >
                    <i className="bi bi-send"></i> Publicar
                  </BotonCargando>
                </div>
              </div>

              <div className="gm-tabs" role="tablist">
                {bloques.map((b) => {
                  const total = malla.turnos
                    .filter((t) => t.bloque.nombre_bloque === b.nombre_bloque)
                    .reduce((n, t) => n + t.asignaciones.length, 0);
                  return (
                    <button
                      key={b.nombre_bloque}
                      type="button"
                      role="tab"
                      aria-selected={b.nombre_bloque === bloqueActivo}
                      className={`gm-tab ${b.nombre_bloque === bloqueActivo ? 'activo' : ''}`}
                      onClick={() => cambiarBloque(b)}
                    >
                      <span className="gm-tab-nombre">{nombreTurno(b)}</span>
                      <span className="gm-tab-horario">{horarioBloque(b)}</span>
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
                            <Cupos asignados={turno.asignaciones.length} cupos={turno.cupos} />
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
                                    <th className="gm-col-acciones"></th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {turno.asignaciones.map((a) => {
                                    const enMovimiento = moviendo?.id === a.id_asignacion;
                                    return [
                                      <tr key={a.id_asignacion}>
                                        <td className="gm-nombre">{a.usuario_nombre}</td>
                                        <td className="gm-mono">{a.rut ?? '—'}</td>
                                        <td>{a.correo ?? '—'}</td>
                                        <td>{a.contrato ?? '—'}</td>
                                        <td>{a.maquina ?? '—'}</td>
                                        <td>{a.especialidad ?? '—'}</td>
                                        <td>
                                          <EstadoBadge estado={a.estado} />
                                        </td>
                                        <td className="gm-col-acciones">
                                          <div className="gm-acciones-fila">
                                            <BotonCargando
                                              className={`gm-btn-icono ${enMovimiento ? 'activo' : ''}`}
                                              title="Mover a otro turno"
                                              disabled={!editable}
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                setMoviendo(
                                                  enMovimiento ? null : { id: a.id_asignacion, destino: '' }
                                                );
                                              }}
                                            >
                                              <i className="bi bi-arrow-left-right"></i>
                                            </BotonCargando>
                                            <BotonCargando
                                              className="gm-btn-quitar"
                                              title={
                                                publicada
                                                  ? 'Quitar (quedará como reemplazado)'
                                                  : 'Quitar de este turno'
                                              }
                                              disabled={!editable}
                                              cargando={accion === `quitar-${a.id_asignacion}`}
                                              textoCargando={null}
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleQuitar(a.id_asignacion);
                                              }}
                                            >
                                              <i className="bi bi-x-lg"></i>
                                            </BotonCargando>
                                          </div>
                                        </td>
                                      </tr>,
                                      enMovimiento && (
                                        <tr key={`mover-${a.id_asignacion}`} className="gm-fila-mover">
                                          <td colSpan={8} onClick={(e) => e.stopPropagation()}>
                                            <div className="gm-mover">
                                              <span>
                                                Mover a <strong>{a.usuario_nombre}</strong> a:
                                              </span>
                                              <select
                                                className="gm-input"
                                                value={moviendo.destino}
                                                onChange={(e) =>
                                                  setMoviendo({ ...moviendo, destino: e.target.value })
                                                }
                                              >
                                                <option value="">Selecciona un turno…</option>
                                                {destinosPorBloque(turno.id_turno).map(({ bloque, turnos }) =>
                                                  turnos.length === 0 ? null : (
                                                    <optgroup
                                                      key={bloque.nombre_bloque}
                                                      label={`${nombreTurno(bloque)} (${horarioBloque(bloque)})`}
                                                    >
                                                      {turnos.map((t) => (
                                                        <option key={t.id_turno} value={t.id_turno}>
                                                          {nombreTurno(bloque)} · {t.area} · {t.puesto} (
                                                          {t.asignaciones.length}/{t.cupos})
                                                        </option>
                                                      ))}
                                                    </optgroup>
                                                  )
                                                )}
                                              </select>
                                              <BotonCargando
                                                className="gm-btn gm-btn-primario"
                                                disabled={!editable || !moviendo.destino}
                                                cargando={accion === `mover-${a.id_asignacion}`}
                                                textoCargando="Moviendo..."
                                                onClick={handleMover}
                                              >
                                                Confirmar
                                              </BotonCargando>
                                              <BotonCargando
                                                className="gm-btn"
                                                disabled={cargando}
                                                onClick={() => setMoviendo(null)}
                                              >
                                                Cancelar
                                              </BotonCargando>
                                            </div>
                                            {publicada && (
                                              <p className="gm-mover-nota">
                                                La asignación actual quedará como reemplazada.
                                              </p>
                                            )}
                                          </td>
                                        </tr>
                                      ),
                                    ];
                                  })}
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
                <i className="bi bi-person-plus"></i> Candidatos
              </div>

              {!turnoSeleccionado ? (
                <p className="gm-muted">Selecciona un turno para ver quién puede ocupar un cupo.</p>
              ) : (
                <>
                  <div className="gm-candidatos-turno">
                    <strong>{turnoSeleccionado.puesto}</strong>
                    <span>
                      {turnoSeleccionado.area} · {horarioBloque(turnoSeleccionado.bloque)}
                    </span>
                    <Cupos
                      asignados={turnoSeleccionado.asignaciones.length}
                      cupos={turnoSeleccionado.cupos}
                      sufijo=" cupos"
                    />
                  </div>

                  {cargandoCandidatos ? (
                    <p className="gm-muted">Buscando candidatos...</p>
                  ) : candidatos.length === 0 ? (
                    <p className="gm-muted">No hay más trabajadores con este puesto.</p>
                  ) : (
                    <>
                      <h4 className="gm-candidatos-seccion">Disponibles ({disponibles.length})</h4>
                      {disponibles.length === 0 ? (
                        <p className="gm-muted">No hay trabajadores aptos para este turno.</p>
                      ) : (
                        <ul className="gm-lista-candidatos">
                          {disponibles.map((c) => (
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
                              <BotonCargando
                                className="gm-btn gm-btn-primario"
                                disabled={!editable}
                                cargando={accion === `asignar-${c.id_usuario}`}
                                onClick={() => handleAsignar(c.id_usuario)}
                              >
                                Asignar
                              </BotonCargando>
                            </li>
                          ))}
                        </ul>
                      )}

                      {noAsignables.length > 0 && (
                        <>
                          <h4 className="gm-candidatos-seccion">No asignables ({noAsignables.length})</h4>
                          <ul className="gm-lista-candidatos">
                            {noAsignables.map((c) => (
                              <li key={c.id_usuario} className="gm-candidato-bloqueado">
                                <div className="gm-candidato-info">
                                  <div className="gm-nombre">
                                    <i className="bi bi-slash-circle"></i> {c.nombre}
                                  </div>
                                  <div className="gm-candidato-meta">
                                    <span className="gm-mono">{c.rut ?? '—'}</span>
                                    <span>{c.horas_semana} h esta semana</span>
                                  </div>
                                  <ul className="gm-motivos">
                                    {c.motivos.map((motivo) => (
                                      <li key={motivo}>{motivo}</li>
                                    ))}
                                  </ul>
                                </div>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </>
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
