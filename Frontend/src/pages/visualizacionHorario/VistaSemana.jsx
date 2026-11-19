import { Fragment, useEffect, useState } from 'react';
import horarioVistaService from '../../services/horarioVista';
import { mensajeError } from '../../services/api';
import {
  diaCorto, diaSemana, fechaCorta, formatearFecha, hoyISO, lunesDe, sumarDias,
} from './fechas';

// Estados de un día en "Mi semana" (los define el backend).
const ESTADOS_DIA = {
  descanso: { icono: 'bi-cup-hot', texto: 'Descanso' },
  no_publicada: { icono: 'bi-hourglass-split', texto: 'Horario aún no publicado' },
  sin_malla: { icono: 'bi-calendar-x', texto: 'Sin horario' },
};

const salida = (t) => `${t.hora_termino}${t.cruza_medianoche ? ' (+1 día)' : ''}`;

// ------------------------------------------------------------------ Trabajador

const TurnoDelDia = ({ turno }) => (
  <div className="hor-dia-turno">
    <div className="hor-dia-turno-bloque">{turno.orden}° turno</div>
    <div className="hor-dia-turno-horario">
      <span><i className="bi bi-box-arrow-in-right"></i> Entrada {turno.hora_inicio}</span>
      <span><i className="bi bi-box-arrow-right"></i> Salida {salida(turno)}</span>
    </div>
    <div className="hor-dia-turno-detalle">
      <span><i className="bi bi-geo-alt"></i> {turno.area}</span>
      <span><i className="bi bi-person-gear"></i> {turno.funcion}</span>
      {turno.maquina && <span><i className="bi bi-truck"></i> {turno.maquina}</span>}
    </div>
  </div>
);

const MiSemana = ({ dias, hoy }) => (
  <div className="hor-semana-grid">
    {dias.map((dia) => {
      const estado = ESTADOS_DIA[dia.estado];
      return (
        <article
          key={dia.fecha}
          className={`hor-dia-card ${dia.estado} ${dia.fecha === hoy ? 'hoy' : ''}`}
          aria-label={`${diaSemana(dia.fecha)} ${formatearFecha(dia.fecha)}`}
        >
          <header className="hor-dia-cabecera">
            <span className="hor-dia-nombre">{diaSemana(dia.fecha)}</span>
            <span className="hor-dia-fecha">{fechaCorta(dia.fecha)}</span>
            {dia.fecha === hoy && <span className="hor-tu">Hoy</span>}
          </header>

          {dia.sale_de_nocturno && (
            <div className="hor-dia-nota">
              <i className="bi bi-moon-stars"></i> Sales del turno nocturno a las {dia.sale_de_nocturno}
            </div>
          )}

          {dia.turnos.length > 0 ? (
            dia.turnos.map((t) => <TurnoDelDia key={`${t.id_bloque}-${t.area}-${t.funcion}`} turno={t} />)
          ) : (
            <div className={`hor-dia-estado ${dia.estado}`}>
              <i className={`bi ${estado?.icono ?? 'bi-dash-circle'}`}></i>
              <span>{estado?.texto ?? dia.estado}</span>
            </div>
          )}
        </article>
      );
    })}
  </div>
);

// ------------------------------------------------------------------ Encargado / administrador

const MarcaDia = ({ dia }) => {
  if (!dia.malla) return <span className="hor-matriz-marca muted">Sin malla</span>;
  if (dia.publicada) return null;
  return dia.visible
    ? <span className="hor-matriz-marca borrador">Borrador</span>
    : <span className="hor-matriz-marca muted">No publicada</span>;
};

const totalesPorColumna = (matriz, dias, bloques) =>
  dias.map((_, i) =>
    bloques.map((b) =>
      matriz
        .filter((g) => !g.sin_turnos)
        .reduce((n, g) => n + g.trabajadores.filter((t) => t.turnos[i].includes(b.orden)).length, 0),
    ),
  );

const MatrizSemana = ({ data, hoy }) => {
  const { dias, bloques, matriz } = data;
  const columnas = 2 + dias.length * bloques.length;
  const borradores = dias.filter((d) => d.malla && !d.publicada && d.visible);
  const totales = totalesPorColumna(matriz, dias, bloques);

  const claseCelda = (i, j) =>
    [j === 0 ? 'inicio-dia' : '', dias[i].fecha === hoy ? 'hoy' : '', dias[i].visible ? '' : 'oculta']
      .filter(Boolean)
      .join(' ');

  return (
    <>
      {data.puede_editar && borradores.length > 0 && (
        <div className="hor-aviso">
          <i className="bi bi-exclamation-triangle"></i>
          <span>
            <strong>Borrador:</strong> {borradores.map((d) => diaCorto(d.fecha)).join(', ')}{' '}
            {borradores.length === 1 ? 'aún no está publicado' : 'aún no están publicados'}. Los trabajadores todavía no lo ven.
          </span>
        </div>
      )}

      {matriz.length === 0 ? (
        <div className="hor-panel">
          <div className="hor-vacio">
            <i className="bi bi-people"></i>
            <p>No hay trabajadores para mostrar esta semana.</p>
          </div>
        </div>
      ) : (
        <div className="hor-matriz-scroll">
          <table className="hor-matriz">
            <thead>
              <tr>
                <th rowSpan={2} className="fija codigo">Código</th>
                <th rowSpan={2} className="fija nombre">Nombre</th>
                {dias.map((d) => (
                  <th
                    key={d.fecha}
                    colSpan={bloques.length}
                    className={`dia inicio-dia ${d.fecha === hoy ? 'hoy' : ''}`}
                  >
                    <div>{diaCorto(d.fecha)}</div>
                    <MarcaDia dia={d} />
                  </th>
                ))}
              </tr>
              <tr>
                {dias.map((d, i) =>
                  bloques.map((b, j) => (
                    <th
                      key={`${d.fecha}-${b.orden}`}
                      className={`turno ${claseCelda(i, j)}`}
                      title={`${b.orden}° turno · ${b.hora_inicio} – ${b.hora_termino}`}
                    >
                      {b.orden}°
                    </th>
                  )),
                )}
              </tr>
            </thead>
            <tbody>
              {matriz.map((grupo) => (
                <Fragment key={grupo.funcion}>
                  <tr className={`grupo ${grupo.sin_turnos ? 'sin-turnos' : ''}`}>
                    <th colSpan={columnas}>
                      <span className="hor-matriz-grupo">
                        {grupo.funcion}
                        <span className="hor-matriz-cuenta">{grupo.trabajadores.length}</span>
                      </span>
                    </th>
                  </tr>
                  {grupo.trabajadores.map((t) => (
                    <tr key={`${grupo.funcion}-${t.codigo}`} className={grupo.sin_turnos ? 'sin-turnos' : ''}>
                      <td className="fija codigo">{t.codigo}</td>
                      <td className="fija nombre">{t.nombre}</td>
                      {t.turnos.map((ordenes, i) =>
                        bloques.map((b, j) => {
                          const asignado = ordenes.includes(b.orden);
                          return (
                            <td
                              key={`${i}-${b.orden}`}
                              className={`celda ${asignado ? 'asignado' : ''} ${claseCelda(i, j)}`}
                            >
                              {asignado ? 1 : ''}
                            </td>
                          );
                        }),
                      )}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th className="fija codigo"></th>
                <th className="fija nombre">Total</th>
                {totales.map((porBloque, i) =>
                  porBloque.map((n, j) => (
                    <td key={`total-${i}-${j}`} className={`celda total ${claseCelda(i, j)}`}>
                      {n || ''}
                    </td>
                  )),
                )}
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </>
  );
};

// ------------------------------------------------------------------ Vista

const VistaSemana = () => {
  const hoy = hoyISO();
  const semanaActual = lunesDe(hoy);
  const [desde, setDesde] = useState(semanaActual);
  const [data, setData] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let vigente = true;
    horarioVistaService
      .obtenerSemana(desde)
      .then((respuesta) => vigente && setData(respuesta))
      .catch((err) => {
        if (!vigente) return;
        setData(null);
        setError(mensajeError(err, 'No se pudo cargar el horario semanal.'));
      })
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [desde]);

  const cambiarSemana = (fecha) => {
    if (!fecha) return;
    const lunes = lunesDe(fecha);
    if (lunes === desde) return;
    setCargando(true);
    setError('');
    setDesde(lunes);
  };

  const hasta = sumarDias(desde, 6);
  const esTrabajador = Array.isArray(data?.mi_semana);

  return (
    <div className="hor-contenedor hor-contenedor-ancho">
      <div className="hor-controles">
        <div className="hor-fecha">
          <button type="button" className="hor-icono" title="Semana anterior" onClick={() => cambiarSemana(sumarDias(desde, -7))}>
            <i className="bi bi-chevron-left"></i>
          </button>
          <span className="hor-semana-rango">
            {fechaCorta(desde)} al {formatearFecha(hasta)}
          </span>
          <button type="button" className="hor-icono" title="Semana siguiente" onClick={() => cambiarSemana(sumarDias(desde, 7))}>
            <i className="bi bi-chevron-right"></i>
          </button>
          <input
            type="date"
            className="form-control hor-input"
            aria-label="Ir a la semana de"
            value={desde}
            onChange={(e) => cambiarSemana(e.target.value)}
          />
          {desde !== semanaActual && (
            <button type="button" className="hor-chip" onClick={() => cambiarSemana(hoy)}>
              Esta semana
            </button>
          )}
        </div>
        {data && (
          <h2 className="hor-semana-titulo">{esTrabajador ? 'Mi semana' : 'Turnos del equipo'}</h2>
        )}
      </div>

      {error && <div className="alert alert-danger p-2">{error}</div>}

      {cargando && !data && <p className="hor-muted">Cargando...</p>}

      {data && (
        <div className={cargando ? 'hor-cargando' : ''}>
          {esTrabajador ? (
            <MiSemana dias={data.mi_semana} hoy={hoy} />
          ) : (
            <MatrizSemana data={data} hoy={hoy} />
          )}
        </div>
      )}
    </div>
  );
};

export default VistaSemana;
