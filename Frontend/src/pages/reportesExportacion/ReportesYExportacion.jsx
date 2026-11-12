import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/auth';
import TextoRol from '../../components/TextoRol';
import horarioService from '../../services/horario';
import '../home/home.css';
import '../mallaDeTurnos/gestionMalla.css';
import './ReportesYExportacion.css';

const RUTA_HOME = '/home';
const ROL_PLANIFICADOR = 2;

const hoyISO = () => new Date().toLocaleDateString('en-CA');

const primerDiaDelMesISO = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toLocaleDateString('en-CA');
};

const formatearFecha = (iso) => {
  const [a, m, d] = iso.split('-');
  return `${d}-${m}-${a}`;
};

const mensajeError = (err) => {
  const data = err.response?.data;
  if (!data) return 'Error de conexión.';
  if (data.detail) return data.detail;
  return Object.values(data).flat().join(' ') || 'Ocurrió un error.';
};

const ReportesYExportacion = () => {
  const [usuario, setUsuario] = useState(null);
  const [mallasPublicadas, setMallasPublicadas] = useState([]);
  const [cargandoMallas, setCargandoMallas] = useState(true);
  const [mallaId, setMallaId] = useState('');
  const [bloque, setBloque] = useState('');
  const [desde, setDesde] = useState(primerDiaDelMesISO());
  const [hasta, setHasta] = useState(hoyISO());
  const [estado, setEstado] = useState('');
  const [descargando, setDescargando] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    if (currentUser.id_rol !== ROL_PLANIFICADOR) {
      navigate(RUTA_HOME);
      return;
    }
    setUsuario(currentUser);

    horarioService
      .listarMallas()
      .then((mallas) => {
        const publicadas = mallas.filter((m) => m.estado === 'publicada');
        setMallasPublicadas(publicadas);
        if (publicadas.length > 0) setMallaId(String(publicadas[0].id_malla));
      })
      .catch(() => setError('No se pudieron cargar las mallas.'))
      .finally(() => setCargandoMallas(false));
  }, [navigate]);

  const descargar = async (clave, fn) => {
    setError('');
    setDescargando(clave);
    try {
      await fn();
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setDescargando('');
    }
  };

  const exportarMalla = () => {
    const malla = mallasPublicadas.find((m) => String(m.id_malla) === mallaId);
    const sufijo = bloque ? `_${bloque}` : '';
    return descargar('malla', () =>
      horarioService.descargarArchivo(
        `reportes/malla/${mallaId}/pdf/`,
        bloque ? { bloque } : {},
        `horario_${malla?.fecha ?? mallaId}${sufijo}.pdf`,
      )
    );
  };

  const exportarInasistencias = () =>
    descargar('inasistencias', () =>
      horarioService.descargarArchivo(
        'reportes/inasistencias/pdf/',
        { desde, hasta, estado: estado || undefined },
        `inasistencias_${desde}_${hasta}.pdf`,
      )
    );

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const rangoInvalido = desde > hasta;

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
        <h1>Reportes y Exportación</h1>
        <p>Exporta horarios publicados e historial de inasistencias en PDF</p>
      </div>

      <div className="gm-contenedor">
        {error && (
          <div className="gm-alerta">
            <i className="bi bi-exclamation-octagon"></i> {error}
          </div>
        )}

        <section className="gm-panel rep-panel">
          <div className="gm-panel-titulo">
            <i className="bi bi-file-earmark-pdf"></i> Horario publicado
          </div>
          <p className="gm-muted rep-descripcion">
            Genera el PDF de la malla definitiva, agrupado por área y bloque de turno.
          </p>

          {cargandoMallas ? (
            <div className="gm-cargando">
              <span className="gm-spinner"></span> Cargando mallas...
            </div>
          ) : mallasPublicadas.length === 0 ? (
            <p className="gm-muted">No hay mallas publicadas para exportar.</p>
          ) : (
            <div className="rep-filtros">
              <label className="rep-campo">
                <span>Malla</span>
                <select
                  className="gm-input"
                  value={mallaId}
                  onChange={(e) => setMallaId(e.target.value)}
                >
                  {mallasPublicadas.map((m) => (
                    <option key={m.id_malla} value={m.id_malla}>
                      Malla del {formatearFecha(m.fecha)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="rep-campo">
                <span>Bloque</span>
                <select
                  className="gm-input"
                  value={bloque}
                  onChange={(e) => setBloque(e.target.value)}
                >
                  <option value="">Todos los turnos</option>
                  <option value="primer_turno">1° turno</option>
                  <option value="segundo_turno">2° turno</option>
                  <option value="tercer_turno">3° turno</option>
                </select>
              </label>
              <div className="rep-acciones">
                <button
                  className="gm-btn gm-btn-primario"
                  disabled={!mallaId || descargando !== ''}
                  onClick={exportarMalla}
                >
                  <i className="bi bi-download"></i>
                  {descargando === 'malla' ? ' Generando...' : ' Exportar PDF'}
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="gm-panel rep-panel">
          <div className="gm-panel-titulo">
            <i className="bi bi-person-x"></i> Reporte de inasistencias
          </div>
          <p className="gm-muted rep-descripcion">
            Historial de ausencias registradas, filtrado por rango de fechas y estado.
          </p>

          <div className="rep-filtros">
            <label className="rep-campo">
              <span>Desde</span>
              <input
                type="date"
                className="gm-input"
                value={desde}
                onChange={(e) => setDesde(e.target.value)}
              />
            </label>
            <label className="rep-campo">
              <span>Hasta</span>
              <input
                type="date"
                className="gm-input"
                value={hasta}
                onChange={(e) => setHasta(e.target.value)}
              />
            </label>
            <label className="rep-campo">
              <span>Estado</span>
              <select
                className="gm-input"
                value={estado}
                onChange={(e) => setEstado(e.target.value)}
              >
                <option value="">Todos</option>
                <option value="pendiente">Pendiente</option>
                <option value="aprobado">Aprobado</option>
                <option value="rechazado">Rechazado</option>
              </select>
            </label>
          </div>

          {rangoInvalido && (
            <p className="rep-aviso">La fecha "desde" no puede ser posterior a "hasta".</p>
          )}

          <div className="rep-acciones">
            <button
              className="gm-btn gm-btn-primario"
              disabled={rangoInvalido || descargando !== ''}
              onClick={exportarInasistencias}
            >
              <i className="bi bi-download"></i>
              {descargando === 'inasistencias' ? ' Generando...' : ' Exportar PDF'}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};

export default ReportesYExportacion;