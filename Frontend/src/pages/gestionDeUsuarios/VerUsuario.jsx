import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import userService, { competenciaService, rolService } from '../../services/userService';
import TextoRol from '../../components/TextoRol';
import { esTimeout, MENSAJE_TIMEOUT } from '../../services/api';
import './GestionDeUsuarios.css';

const ROJO = '#F2867D';

// "2026-11-20" -> "20-11-2026" sin pasar por Date (evita el desfase de zona horaria).
const formatoFecha = (iso) => (iso ? iso.split('-').reverse().join('-') : 'Sin vencimiento');

const VerUsuario = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [competencias, setCompetencias] = useState(null);
  const [roles, setRoles] = useState([]);
  const [usuarioData, setUsuarioData] = useState(null);
  const [error, setError] = useState(null);

  const [cargando, setCargando] = useState(true);
  useEffect(() => {
    cargarDatosUsuario(id);
  }, [id]);

  const cargarDatosUsuario = async (userId) => {
    try {
      setCargando(true);
      const data = await userService.getUsuarioById(userId);
      setUsuarioData(data);

      setCompetencias(await competenciaService.getCompetencias(userId));

      const respuestaRoles = await rolService.getRoles();
      const listaRoles = Array.isArray(respuestaRoles)
        ? respuestaRoles
        : respuestaRoles.results ?? [];
      setRoles(listaRoles);
    } catch (error) {
      setError(esTimeout(error) ? MENSAJE_TIMEOUT : "No se pudo cargar la información del usuario.");
    } finally {
      setCargando(false);
    }
  };

  const contratoAsignado = competencias?.contrato;

const obtenerNombreRol = (idRol) => {
  const rol = roles.find(
    (rol) => Number(rol.id_rol) === Number(idRol)
  );
  return rol?.nombre_rol ?? 'Rol no asignado';
};
  
  // Estilos centralizados para mejorar la visibilidad en modo oscuro
  const labelStyle = {
    fontSize: '13px', 
    textTransform: 'uppercase', 
    letterSpacing: '0.05em',
    color: '#A0B2C6', // Color mucho más claro para que resalte
    fontWeight: '600',
    marginBottom: '8px',
    display: 'block'
  };
  const valueBoxStyle = {
    backgroundColor: 'rgba(10, 20, 32, 0.5)', 
    border: '1px solid #1E3349', 
    borderRadius: '8px',
    padding: '14px 16px',
    color: '#E9EEF5', // Texto principal en blanco/gris muy claro
    fontSize: '15px'
  };
  return (
    <div className="up-shell">
      <div className="up-topbar">
        <div className="up-brand">
          <img src="/logo/logo-ultraport-color.svg" alt="Ultraport" className="up-logo" />
          <span className="sub">Panel de Turnos<TextoRol /></span>
        </div>
      </div>
      <div className="up-subbar">
        <button onClick={() => navigate('/usuarios')} className="up-back">
          <i className="bi bi-arrow-left"></i> Volver a Usuarios
        </button>
      </div>
      <div className="up-hero mb-4">
        <h1>Detalles del Usuario </h1>
        <p>Información completa registrada en el sistema</p>
      </div>
      <div className="up-dashboard-container" style={{maxWidth: '800px'}}>
        <div className="up-table-wrapper p-4 p-md-5" style={{textAlign: 'left'}}>
          {error && (
            <div className="alert alert-danger" style={{backgroundColor: 'rgba(226, 87, 76, 0.1)', color: '#F2867D', border: '1px solid #E2574C'}}>
              {error}
            </div>
          )}
          {cargando ? (
            <div className="text-center py-5 text-light">
              <div className="spinner-border text-warning mb-3" role="status"></div>
              <div>Cargando información...</div>
            </div>
          ) : usuarioData && (
            <div>
              <div className="d-flex flex-column flex-md-row align-items-center align-items-md-start gap-4 mb-5 pb-4" style={{borderBottom: '1px solid #1E3349'}}>
                <div 
                  className="d-flex align-items-center justify-content-center flex-shrink-0" 
                  style={{ width: '90px', height: '90px', borderRadius: '50%', backgroundColor: 'rgba(242, 166, 61, 0.1)', color: '#F2A63D', fontSize: '40px' }}
                >
                  <i className="bi bi-person-fill"></i>
                </div>
                <div className="text-center text-md-start">
                  <h3 className="text-light mb-1" style={{fontSize: '24px', fontWeight: 'bold'}}>
                    {usuarioData.nombres} {usuarioData.apellidos}
                  </h3>
                  <p style={{color: '#A0B2C6', fontSize: '16px', margin: 0}}>
                    {obtenerNombreRol(usuarioData.id_rol)}
                  </p>
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label style={labelStyle}>RUT</label>
                  <div style={valueBoxStyle}>{usuarioData.rut}</div>
                </div>
                <div className="col-md-6 mt-3 mt-md-0">
                  <label style={labelStyle}>Correo Electrónico</label>
                  <div style={valueBoxStyle}>{usuarioData.correo}</div>
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label style={labelStyle}>Rol del Sistema</label>
                  <div style={valueBoxStyle}>
                    <i className="bi bi-shield-check me-2 text-warning"></i>
                    {obtenerNombreRol(usuarioData.id_rol)}
                  </div>
                </div>
                <div className="col-md-6 mt-3 mt-md-0">
                  <label style={labelStyle}>Contrato Asignado</label>
                  <div style={valueBoxStyle}>
                    {contratoAsignado ? 
                    (
                      <>
                        <i className="bi bi-file-earmark-text me-2" style={{ color: '#3D8BF2' }}/>
                        {contratoAsignado.tipo_display}
                        {contratoAsignado.modalidad && ` · ${contratoAsignado.modalidad}`}
                        <div style={{ color: '#A0B2C6', fontSize: '13px', marginTop: '4px' }}>
                          Turno {contratoAsignado.turno_habitual} · {contratoAsignado.horas_semanales_pactadas} h/semana
                          {contratoAsignado.fecha_termino && ` · termina ${formatoFecha(contratoAsignado.fecha_termino)}`}
                        </div>
                        </>
                    ) :
                    (
                      <span style={{ color: '#E2574C' }}>
                        <i className="bi bi-exclamation-circle me-2" />
                        Sin contrato asignado
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label style={labelStyle}>Estado de Cuenta</label>
                  <div style={{...valueBoxStyle, minHeight: '52px', display: 'flex', alignItems: 'center'}}>
                    <span className={`badge rounded-pill up-status-badge ${usuarioData.estado === 'activo' ? 'active' : 'inactive'}`}>
                      {usuarioData.estado}
                    </span>
                  </div>
                </div>
                <div className="col-md-6 mt-3 mt-md-0">
                  <label style={labelStyle}>Fecha de Registro</label>
                  <div style={valueBoxStyle}>
                    <i className="bi bi-calendar3 me-2" ></i>
                    {usuarioData.fecha_creacion ? new Date(usuarioData.fecha_creacion).toLocaleDateString('es-CL', {
                      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    }) : 'No disponible'}
                  </div>
                </div>
              </div>

              {competencias && (
                <div className="mt-5 pt-4" style={{borderTop: '1px solid #1E3349'}}>
                  <h5 className="text-light mb-4">Competencias</h5>

                  <div className="mb-4">
                    <label style={labelStyle}>Puestos</label>
                    <div style={valueBoxStyle}>
                      {competencias.puestos.length === 0 ? (
                        <span style={{color: '#A0B2C6'}}>Sin puestos asignados</span>
                      ) : (
                        <div className="d-flex flex-wrap gap-2">
                          {competencias.puestos.map((p) => (
                            <span key={p.id_puesto} className="badge rounded-pill"
                              style={{backgroundColor: 'rgba(61, 139, 242, 0.15)', color: '#8DB9F7', fontSize: '13px'}}>
                              {p.nombre_puesto}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mb-4">
                    <label style={labelStyle}>Licencias</label>
                    {competencias.licencias.length === 0 ? (
                      <div style={{...valueBoxStyle, color: '#A0B2C6'}}>Sin licencias registradas</div>
                    ) : (
                      <div style={valueBoxStyle}>
                        <table className="table table-sm table-borderless mb-0" style={{'--bs-table-bg': 'transparent', color: 'inherit'}}>
                          <thead>
                            <tr style={{color: '#A0B2C6', fontSize: '13px'}}>
                              <th style={{color: 'inherit'}}>Tipo</th>
                              <th style={{color: 'inherit'}}>Emisión</th>
                              <th style={{color: 'inherit'}}>Vencimiento</th>
                            </tr>
                          </thead>
                          <tbody>
                            {competencias.licencias.map((l) => {
                              const color = l.vencida ? ROJO : '#E9EEF5';
                              return (
                                <tr key={l.id_usuario_licencia}>
                                  <td style={{color}}>
                                    {l.vencida && <i className="bi bi-exclamation-circle me-2" />}
                                    {l.nombre_licencia}
                                  </td>
                                  <td style={{color}}>{formatoFecha(l.fecha_emision)}</td>
                                  <td style={{color, fontWeight: l.vencida ? 600 : 400}}>
                                    {formatoFecha(l.fecha_vencimiento)}{l.vencida && ' · Vencida'}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  <div className="mb-2">
                    <label style={labelStyle}>Maquinaria certificada</label>
                    {competencias.maquinarias.length === 0 ? (
                      <div style={{...valueBoxStyle, color: '#A0B2C6'}}>Sin certificaciones registradas</div>
                    ) : (
                      <div style={valueBoxStyle}>
                        <table className="table table-sm table-borderless mb-0" style={{'--bs-table-bg': 'transparent', color: 'inherit'}}>
                          <thead>
                            <tr style={{color: '#A0B2C6', fontSize: '13px'}}>
                              <th style={{color: 'inherit'}}>Máquina</th>
                              <th style={{color: 'inherit'}}>Vencimiento</th>
                            </tr>
                          </thead>
                          <tbody>
                            {competencias.maquinarias.map((m) => {
                              const color = m.vencida ? ROJO : '#E9EEF5';
                              return (
                                <tr key={m.id_usuario_maquinaria}>
                                  <td style={{color}}>
                                    {m.vencida && <i className="bi bi-exclamation-circle me-2" />}
                                    {m.nombre_maquinaria}
                                  </td>
                                  <td style={{color, fontWeight: m.vencida ? 600 : 400}}>
                                    {formatoFecha(m.fecha_vencimiento)}{m.vencida && ' · Vencida'}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default VerUsuario;