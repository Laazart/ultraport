import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import TextoRol from '../../components/TextoRol';
import horarioVistaService from '../../services/horarioVista';
import horarioService from '../../services/horario';
import { mensajeError } from '../../services/api';
import VistaSemana from './VistaSemana';
import { diaSemana, formatearFecha, hoyISO, rangoHorario, sumarDias } from './fechas';
import '../home/home.css';
import './visualizacionHorario.css';

const RUTA_HOME = '/home';
const RUTA_GESTION = '/malla/gestion';
const FAENA_GENERAL = 'General';
const ROL_TRABAJADOR = 3;

const MODOS = [
  { valor: 'dia', etiqueta: 'Día', icono: 'bi-calendar-day' },
  { valor: 'semana', etiqueta: 'Semana', icono: 'bi-calendar-week' },
];

const bloqueInicial = (data) => {
  if (data.mis_turnos?.length) return data.mis_turnos[0].id_bloque;
  return (data.bloques.find((b) => b.total > 0) || data.bloques[0])?.id_bloque ?? null;
};

const EstadoVacio = ({ icono, texto }) => (
  <div className="hor-vacio">
    <i className={`bi ${icono}`}></i>
    <p>{texto}</p>
  </div>
);

const tituloMisTurnos = (cantidad, fecha, esHoy) => {
  const base = cantidad > 1 ? 'Tus turnos' : 'Tu turno';
  return esHoy ? `${base} de hoy` : `${base} del ${formatearFecha(fecha)}`;
};

const TarjetaMisTurnos = ({ turnos, fecha, esHoy }) => (
  <div className="hor-mi-turno">
    <div className="hor-mi-turno-titulo">
      <i className="bi bi-person-badge"></i>
      {tituloMisTurnos(turnos.length, fecha, esHoy)}
    </div>
    {turnos.map((turno) => (
      <div key={`${turno.id_bloque}-${turno.area}-${turno.funcion}`} className="hor-mi-turno-item">
        <div className="hor-mi-turno-bloque">
          {turno.orden}° turno · {rangoHorario(turno)}
        </div>
        <div className="hor-mi-turno-detalle">
          <span><i className="bi bi-geo-alt"></i> {turno.area}</span>
          <span><i className="bi bi-person-gear"></i> {turno.funcion}</span>
          {turno.maquina && <span><i className="bi bi-truck"></i> {turno.maquina}</span>}
        </div>
      </div>
    ))}
  </div>
);

const TablaTrabajadores = ({ trabajadores }) => {
  const conMaquina = trabajadores.some((t) => t.maquina);
  return (
    <div className="table-responsive">
      <table className="hor-tabla">
        <thead>
          <tr>
            <th>Código</th>
            <th>Nombre trabajador</th>
            <th>Función operativa</th>
            {conMaquina && <th>Máquina</th>}
          </tr>
        </thead>
        <tbody>
          {trabajadores.map((t, i) => (
            <tr key={`${t.codigo}-${i}`} className={t.es_mio ? 'hor-fila-mia' : ''}>
              <td className="hor-codigo">{t.codigo}</td>
              <td>
                {t.nombre}
                {t.es_mio && <span className="hor-tu">Tú</span>}
              </td>
              <td>{t.funcion}</td>
              {conMaquina && <td>{t.maquina || '—'}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const GrupoArea = ({ area }) => {
  const mostrarFaenas = area.faenas.some((f) => f.faena !== FAENA_GENERAL);
  return (
    <section className="hor-area">
      <h3 className="hor-area-titulo">{area.area}</h3>
      {area.faenas.map((f) => (
        <div key={f.faena} className="hor-faena">
          {mostrarFaenas && <h4 className="hor-faena-titulo">{f.faena}</h4>}
          <TablaTrabajadores trabajadores={f.trabajadores} />
        </div>
      ))}
    </section>
  );
};

const DetalleBloque = ({ bloque, fecha, generadoEn }) => (
  <>
    <div className="hor-encabezado">
      <div>
        <div className="hor-encabezado-titulo">
          {bloque.orden}° turno · {diaSemana(fecha)} {formatearFecha(fecha)}
        </div>
        <div className="hor-encabezado-sub">{rangoHorario(bloque)}</div>
      </div>
      <div className="hor-encabezado-meta">
        <div>{bloque.total} {bloque.total === 1 ? 'trabajador' : 'trabajadores'}</div>
        <div>Actualizado a las {generadoEn}</div>
      </div>
    </div>

    {bloque.areas.length === 0 ? (
      <EstadoVacio icono="bi-people" texto="No hay trabajadores asignados en este turno." />
    ) : (
      bloque.areas.map((a) => <GrupoArea key={a.area} area={a} />)
    )}
  </>
);

const VistaDia = () => {
  const navigate = useNavigate();
  const hoy = hoyISO();
  const [fecha, setFecha] = useState(hoy);
  const [data, setData] = useState(null);
  const [bloqueActivo, setBloqueActivo] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let vigente = true;
    horarioVistaService
      .obtenerDia(fecha)
      .then((respuesta) => {
        if (!vigente) return;
        setData(respuesta);
        setBloqueActivo(bloqueInicial(respuesta));
      })
      .catch((err) => {
        if (!vigente) return;
        setData(null);
        setError(mensajeError(err, 'No se pudo cargar el horario.'));
      })
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [fecha]);

  const cambiarFecha = (nueva) => {
    if (!nueva || nueva === fecha) return;
    setCargando(true);
    setError('');
    setFecha(nueva);
  };

  const descargarPdf = () => {
    if (!data?.malla) return;
    const idMalla = data.malla.id_malla ?? data.malla;
    horarioService
      .descargarArchivo(`reportes/malla/${idMalla}/pdf/`, {}, `horario_${fecha}.pdf`)
      .catch((err) => setError(mensajeError(err, 'No se pudo generar el PDF.')));
  };

  const bloque = data?.bloques.find((b) => b.id_bloque === bloqueActivo);
  const noPublicada = data?.malla && !data.publicada;

  return (
    <div className="hor-contenedor">
      <div className="hor-controles">
        <div className="hor-fecha">
          <button type="button" className="hor-icono" title="Día anterior" onClick={() => cambiarFecha(sumarDias(fecha, -1))}>
            <i className="bi bi-chevron-left"></i>
          </button>
          <input type="date" className="form-control hor-input" value={fecha} onChange={(e) => cambiarFecha(e.target.value)} />
          <button type="button" className="hor-icono" title="Día siguiente" onClick={() => cambiarFecha(sumarDias(fecha, 1))}>
            <i className="bi bi-chevron-right"></i>
          </button>
          {fecha !== hoy && (
            <button type="button" className="hor-chip" onClick={() => cambiarFecha(hoy)}>
              Hoy
            </button>
          )}
        </div>

        <div className="hor-acciones">
          {data?.malla && data.publicada && (
            <button type="button" className="hor-btn hor-btn-outline" onClick={descargarPdf}>
              <i className="bi bi-file-earmark-pdf"></i>
              Descargar PDF
            </button>
          )}

          {data?.puede_editar && (
            <button
              type="button"
              className="hor-btn"
              onClick={() => {
                const orden = data.bloques.find((b) => b.id_bloque === bloqueActivo)?.orden;
                navigate(`${RUTA_GESTION}?fecha=${fecha}${orden ? `&turno=${orden}` : ''}`);
              }}
            >
              <i className="bi bi-pencil-square"></i>
              Editar / Realizar asignaciones
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-danger p-2">{error}</div>}

      {cargando && !data && <p className="hor-muted">Cargando...</p>}

      {data && (
        <div className={cargando ? 'hor-cargando' : ''}>
          {data.mis_turnos?.length > 0 && (
            <TarjetaMisTurnos turnos={data.mis_turnos} fecha={fecha} esHoy={fecha === hoy} />
          )}

          {noPublicada && data.puede_editar && (
            <div className="hor-aviso">
              <i className="bi bi-exclamation-triangle"></i>
              <span><strong>Borrador:</strong> esta malla aún no está publicada. Los trabajadores todavía no la ven.</span>
            </div>
          )}

          {!data.malla ? (
            <div className="hor-panel">
              <EstadoVacio icono="bi-calendar-x" texto="No hay horario para esta fecha." />
            </div>
          ) : noPublicada && !data.puede_editar ? (
            <div className="hor-panel">
              <EstadoVacio icono="bi-hourglass-split" texto="Horario aún no publicado." />
            </div>
          ) : (
            <div className="hor-panel">
              <div className="hor-tabs" role="tablist">
                {data.bloques.map((b) => (
                  <button
                    key={b.id_bloque}
                    type="button"
                    role="tab"
                    aria-selected={b.id_bloque === bloqueActivo}
                    className={`hor-tab ${b.id_bloque === bloqueActivo ? 'activo' : ''}`}
                    onClick={() => setBloqueActivo(b.id_bloque)}
                  >
                    <span className="hor-tab-nombre">{b.orden}° turno</span>
                    <span className="hor-tab-horario">{rangoHorario(b)}</span>
                    <span className="hor-tab-total">{b.total}</span>
                  </button>
                ))}
              </div>

              {bloque && <DetalleBloque bloque={bloque} fecha={fecha} generadoEn={data.generado_en} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const VisualizacionHorario = () => {
  const [usuario, setUsuario] = useState(null);
  const [modo, setModo] = useState('dia');
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
        <h1>{modo === 'semana' ? 'Horario semanal' : 'Horario del día'}</h1>
        <p>
          {modo === 'dia'
            ? 'Asignaciones por turno, área y función operativa'
            : Number(usuario?.id_rol) === ROL_TRABAJADOR
              ? 'Tus turnos de lunes a domingo: entrada, salida y descansos'
              : 'Asignaciones de la semana por función y turno'}
        </p>
      </div>

      <div className="hor-modo-barra">
        <div className="hor-modo" role="tablist" aria-label="Vista del horario">
          {MODOS.map((m) => (
            <button
              key={m.valor}
              type="button"
              role="tab"
              aria-selected={modo === m.valor}
              className={`hor-modo-opcion ${modo === m.valor ? 'activo' : ''}`}
              onClick={() => setModo(m.valor)}
            >
              <i className={`bi ${m.icono}`}></i> {m.etiqueta}
            </button>
          ))}
        </div>
      </div>

      {usuario && (modo === 'semana' ? <VistaSemana /> : <VistaDia />)}
    </div>
  );
};

export default VisualizacionHorario;