import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import userService, {
  contratoService, competenciaService, catalogoService, etiquetaContrato, aplanarErrores,
} from '../../services/userService';
import TextoRol from '../../components/TextoRol';
import BotonCargando from '../../components/BotonCargando';
import { esTimeout, MENSAJE_TIMEOUT } from '../../services/api';
import './GestionDeUsuarios.css';
import { validarRut } from '../../services/tools'

// Claves locales para las filas de licencias y máquinas (no son ids de BD).
let ultimaClave = 0;
const nuevaClave = () => ++ultimaClave;

// Fecha local de hoy en formato YYYY-MM-DD (comparable como texto).
const hoyISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const mensajeDeError = (error, porDefecto) => {
  if (esTimeout(error)) return MENSAJE_TIMEOUT;
  const mensajes = aplanarErrores(error.response?.data);
  return mensajes.length ? mensajes.join(' ') : porDefecto;
};

const FormularioUsuario = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const esModoEdicion = Boolean(id);
  const [contratos, setContratos] = useState([]);
  const [catalogo, setCatalogo] = useState({ puestos: [], tiposLicencia: [], maquinarias: [] });
  const [puestos, setPuestos] = useState([]);
  const [licencias, setLicencias] = useState([]);
  const [maquinarias, setMaquinarias] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const cargarCatalogo = async () => {
      try {
        const [listaPuestos, tiposLicencia, listaMaquinarias] = await Promise.all([
          catalogoService.getPuestos(),
          catalogoService.getTiposLicencia(),
          catalogoService.getMaquinarias(),
        ]);
        setCatalogo({ puestos: listaPuestos, tiposLicencia, maquinarias: listaMaquinarias });
      } catch (error) {
        console.error('Error al cargar catálogos:', error.response?.data || error);
        setError(esTimeout(error) ? MENSAJE_TIMEOUT : 'No se pudieron cargar puestos, licencias y máquinas.');
      }
    };
    cargarCatalogo();
  }, []);

  useEffect(() => {
    const cargarContratos = async () => {
      try {
        const data = await contratoService.getContratos();
        const lista = Array.isArray(data) ? data : data.results;

        if (!Array.isArray(lista)) {
          throw new Error('La respuesta de contratos no es una lista');
        }
        setContratos(lista);
      } catch (error) {
        console.error('Error al cargar contratos:', error.response?.data || error);
        setError(esTimeout(error) ? MENSAJE_TIMEOUT : 'No se pudieron cargar los contratos.');
      }
    };
    cargarContratos();
  }, []);

  const [formData, setFormData] = useState({
    rut: '',
    nombres: '',
    apellidos: '',
    correo: '',
    telefono: '',
    id_contrato: '',
    password: '',
    estado: 'activo',
    id_rol: ''
  });

  const [cargando, setCargando] = useState(esModoEdicion); 
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (esModoEdicion) {
      cargarDatosUsuario(id);
    }
  }, [id, esModoEdicion]);

  const cargarDatosUsuario = async (userId) => {
    try {
      const [data, competencias] = await Promise.all([
        userService.getUsuarioById(userId),
        competenciaService.getCompetencias(userId),
      ]);
      setPuestos(competencias.puestos.map((p) => p.id_puesto));
      setLicencias(competencias.licencias.map((l) => ({
        clave: nuevaClave(),
        id_tipo_licencia: String(l.id_tipo_licencia),
        fecha_emision: l.fecha_emision,
        fecha_vencimiento: l.fecha_vencimiento,
      })));
      setMaquinarias(competencias.maquinarias.map((m) => ({
        clave: nuevaClave(),
        id_maquinaria: String(m.id_maquinaria),
        fecha_vencimiento: m.fecha_vencimiento ?? '',
      })));
      setFormData({
        rut: data.rut || '',
        nombres: data.nombres || '',
        apellidos: data.apellidos || '',
        correo: data.correo || '',
        telefono: data.telefono || '',
        password: '', 
        estado: data.estado || 'activo',
        id_rol: data.id_rol || '',
        id_contrato: data.id_contrato ?? ''
      });
    } catch (error) {
      console.error("Error al cargar el usuario:", error);
      setError(esTimeout(error) ? MENSAJE_TIMEOUT : "No se pudo cargar la información del usuario.");
    } finally {
      setCargando(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // --- Competencias ---

  const nombreLicencia = (idTipo) =>
    catalogo.tiposLicencia.find((t) => String(t.id_tipo_licencia) === String(idTipo))?.nombre_licencia ?? '';

  const togglePuesto = (idPuesto) => {
    setPuestos((actuales) => (actuales.includes(idPuesto)
      ? actuales.filter((p) => p !== idPuesto)
      : [...actuales, idPuesto]));
  };

  const agregarLicencia = () => setLicencias((filas) => [
    ...filas, { clave: nuevaClave(), id_tipo_licencia: '', fecha_emision: '', fecha_vencimiento: '' },
  ]);
  const cambiarLicencia = (clave, campo, valor) => setLicencias((filas) =>
    filas.map((f) => (f.clave === clave ? { ...f, [campo]: valor } : f)));
  const quitarLicencia = (clave) => setLicencias((filas) => filas.filter((f) => f.clave !== clave));

  const agregarMaquinaria = () => setMaquinarias((filas) => [
    ...filas, { clave: nuevaClave(), id_maquinaria: '', fecha_vencimiento: '' },
  ]);
  const cambiarMaquinaria = (clave, campo, valor) => setMaquinarias((filas) =>
    filas.map((f) => (f.clave === clave ? { ...f, [campo]: valor } : f)));
  const quitarMaquinaria = (clave) => setMaquinarias((filas) => filas.filter((f) => f.clave !== clave));

  // Aviso (no bloquea) si la máquina requiere una licencia que no está en la lista o está vencida.
  const avisoLicenciaRequerida = (fila) => {
    const maquina = catalogo.maquinarias.find((m) => String(m.id_maquinaria) === fila.id_maquinaria);
    const requerida = maquina?.id_tipo_licencia_requerida;
    if (!requerida) return null;
    const licencia = licencias.find((l) => l.id_tipo_licencia === String(requerida));
    if (!licencia) return `Requiere licencia ${nombreLicencia(requerida)}, que no tiene.`;
    if (licencia.fecha_vencimiento && licencia.fecha_vencimiento < hoyISO()) {
      return `Requiere licencia ${nombreLicencia(requerida)}, que está vencida.`;
    }
    return null;
  };

  const validarCompetencias = () => {
    for (const l of licencias) {
      if (!l.id_tipo_licencia || !l.fecha_emision || !l.fecha_vencimiento) {
        return 'Completa tipo, emisión y vencimiento de cada licencia (o quita la fila).';
      }
      if (l.fecha_vencimiento <= l.fecha_emision) {
        return `La licencia ${nombreLicencia(l.id_tipo_licencia)} debe vencer después de su emisión.`;
      }
    }
    if (new Set(licencias.map((l) => l.id_tipo_licencia)).size !== licencias.length) {
      return 'Hay licencias repetidas.';
    }
    if (maquinarias.some((m) => !m.id_maquinaria)) {
      return 'Selecciona la máquina de cada certificación (o quita la fila).';
    }
    if (new Set(maquinarias.map((m) => m.id_maquinaria)).size !== maquinarias.length) {
      return 'Hay máquinas repetidas.';
    }
    return null;
  };

  const competenciasAEnviar = () => ({
    puestos,
    licencias: licencias.map((l) => ({
      id_tipo_licencia: Number(l.id_tipo_licencia),
      fecha_emision: l.fecha_emision,
      fecha_vencimiento: l.fecha_vencimiento,
    })),
    maquinarias: maquinarias.map((m) => ({
      id_maquinaria: Number(m.id_maquinaria),
      fecha_vencimiento: m.fecha_vencimiento || null,
    })),
  });

  const handleGuardar = async (e) => {
    e.preventDefault();
    setError(null);
    if (!validarRut(formData.rut)) {
      setError("El RUT ingresado no es válido. Verifica que esté correcto.");
      return;
    }
    const errorCompetencias = validarCompetencias();
    if (errorCompetencias) {
      setError(errorCompetencias);
      return;
    }
    const datosAEnviar = { ...formData, id_contrato: formData.id_contrato ? Number(formData.id_contrato): null};
    if (esModoEdicion && !datosAEnviar.password) {
      delete datosAEnviar.password;
    }
    if (datosAEnviar.id_rol === '') datosAEnviar.id_rol = null;

    setGuardando(true);
    let idUsuario = id;
    try {
      if (esModoEdicion) {
        await userService.actualizarUsuario(id, datosAEnviar);
      } else {
        const creado = await userService.crearUsuario(datosAEnviar);
        idUsuario = creado.id_usuario;
      }
    } catch (error) {
      console.error("Error al guardar:", error.response?.data);
      setError(mensajeDeError(error, "Hubo un error al procesar la solicitud. Revisa los datos."));
      setGuardando(false);
      return;
    }

    let advertencias = [];
    try {
      const respuesta = await competenciaService.guardarCompetencias(idUsuario, competenciasAEnviar());
      advertencias = respuesta.advertencias ?? [];
    } catch (error) {
      console.error("Error al guardar competencias:", error.response?.data);
      const motivo = mensajeDeError(error, "No se pudieron guardar las competencias.");
      if (esModoEdicion) {
        setError(`Los datos del usuario se guardaron, pero no sus competencias: ${motivo}`);
        setGuardando(false);
      } else {
        alert(`El usuario se creó, pero no sus competencias: ${motivo}\nCorrígelas en la edición del usuario.`);
        setGuardando(false);
        navigate(`/usuarios/editar/${idUsuario}`);
      }
      return;
    }

    const titulo = esModoEdicion ? "Usuario actualizado correctamente." : "Usuario creado exitosamente.";
    alert(advertencias.length ? `${titulo}\n\nAdvertencias:\n- ${advertencias.join('\n- ')}` : titulo);
    navigate('/usuarios');
  };

  const labelStyle = {
    fontSize: '13px', 
    textTransform: 'uppercase', 
    letterSpacing: '0.05em',
    color: '#A0B2C6', 
    fontWeight: '600',
    marginBottom: '8px'
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
        <button type="button" onClick={() => navigate('/usuarios')} className="up-back">
          <i className="bi bi-arrow-left"></i> Volver a Usuarios
        </button>
      </div>

      <div className="up-hero mb-4">
        <h1>{esModoEdicion ? 'Editar Usuario' : 'Nuevo Usuario'}</h1>
        <p>{esModoEdicion ? 'Modifica los datos del trabajador' : 'Completa los datos para registrar a un nuevo trabajador'}</p>
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
          ) : (
            <form onSubmit={handleGuardar}>
              {/* izquierda */}
              <div className="row mb-4">
                <div className="col-md-6">
                  <label className="form-label" style={labelStyle}>RUT</label>
                  <input 
                    type="text" 
                    className="form-control up-input" 
                    name="rut"
                    value={formData.rut}
                    onChange={handleChange}
                    placeholder="12.345.678-9"
                    required
                  />
                </div>
                {/* derecha */}
                <div className="col-md-6 mt-3 mt-md-0">
                  <label className="form-label" style={labelStyle}>Correo Electrónico</label>
                  <input 
                    type="email" 
                    className="form-control up-input" 
                    name="correo"
                    value={formData.correo}
                    onChange={handleChange}
                    placeholder="usuario@empresa.cl"
                    required
                  />
                </div>
              </div>
              {/* izquierda */}
              <div className="row mb-4">
                <div className="col-md-6">
                  <label className="form-label" style={labelStyle}>Nombres</label>
                  <input 
                    type="text" 
                    className="form-control up-input" 
                    name="nombres"
                    value={formData.nombres}
                    onChange={handleChange}
                    placeholder="Ej. Juan Carlos"
                    required
                  />
                </div>
                {/* derecha */}
                <div className="col-md-6 mt-3 mt-md-0">
                  <label className="form-label" style={labelStyle}>Apellidos</label>
                  <input 
                    type="text" 
                    className="form-control up-input" 
                    name="apellidos"
                    value={formData.apellidos}
                    onChange={handleChange}
                    placeholder="Ej. Pérez Silva"
                    required
                  />
                </div>
              </div>
              {/* izquierda */}
              <div className="row mb-4">
                <div className="col-md-6">
                    <label className="form-label" style={labelStyle}>
                      Contraseña {esModoEdicion && <span className="text-muted" style={{textTransform: 'none', fontSize: '11px'}}>(Opcional)</span>}
                    </label>
                    <input 
                      type="password" 
                      className="form-control up-input" 
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={esModoEdicion ? "Dejar en blanco para no cambiarla" : "Mínimo 8 caracteres"}
                      required={!esModoEdicion}
                      minLength={8}
                    />
                </div>
                {/* derecha */}
                <div className="col-md-6 mt-3 mt-md-0">
                    <label className="form-label" style={labelStyle}>Rol del Sistema</label>
                    <select 
                      className="form-select up-input" 
                      name="id_rol"
                      value={formData.id_rol}
                      onChange={handleChange}
                      required
                    >
                      {/*5 Administrador | 7 Encargado de Planificacion | 6 Trabajador */}
                      <option value="">Selecciona un rol...</option>
                      <option value="1">Administrador</option>
                      <option value="2">Encargado de Planificacion</option>
                      <option value="3">Trabajador</option>
                    </select>
                </div>
              </div> 
              {/* izquierda */}
              <div className="row mb-4">
                {/*  */}
                  <div className="col-md-6">
                        <label className="form-label" style={labelStyle}>Contrato</label>
                        <select 
                          className="form-select up-input" 
                          name="id_contrato"
                          value={formData.id_contrato}
                          onChange={handleChange}
                          
                        >
                          <option value="">Selecciona un contrato...</option>
                          {contratos.map((contrato) => (
                            <option key={contrato.id_contrato} value={contrato.id_contrato}>
                              {etiquetaContrato(contrato)}
                            </option>
                          ))}
                        </select>
                  </div> 
                {/* derecha */}
                <div className="col-md-6 mt-3 mt-md-0" >
                        <label className="form-label" style={labelStyle}>Telefono</label>
                        <input 
                          type="text" 
                          className="form-control up-input" 
                          name="telefono"
                          value={formData.telefono}
                          onChange={handleChange}
                          placeholder="Ej:947492086"
                          required
                        />
                </div>
              </div>
              <div className="row mb-4">
                  {/* izquierda */}
                  {esModoEdicion && (
                    <div className="col-md-6">
                      
                      <label className="form-label" style=  {labelStyle}>Estado de Cuenta
                      </label>
                      <select 
                        className="form-select up-input" 
                        name="estado"
                        value={formData.estado}
                        onChange={handleChange}
                      >
                        <option value="activo">Activo</option>
                        <option value="inactivo">Inactivo</option>
                      </select>
                    </div>
                  )}
              </div>

              {/* Competencias */}
              <hr style={{borderColor: '#1E3349', margin: '32px 0 24px'}} />
              <h5 className="text-light mb-1">Competencias</h5>
              <p style={{color: '#A0B2C6', fontSize: '13px'}}>
                Puestos, licencias y maquinaria que el validador de asignación considera para los turnos.
              </p>

              <div className="mb-4">
                <label className="form-label" style={labelStyle}>Puestos</label>
                {catalogo.puestos.length === 0 ? (
                  <div style={{color: '#A0B2C6', fontSize: '14px'}}>No hay puestos registrados.</div>
                ) : (
                  <div className="d-flex flex-wrap gap-3">
                    {catalogo.puestos.map((p) => (
                      <div className="form-check" key={p.id_puesto}>
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`puesto-${p.id_puesto}`}
                          checked={puestos.includes(p.id_puesto)}
                          onChange={() => togglePuesto(p.id_puesto)}
                        />
                        <label className="form-check-label text-light" htmlFor={`puesto-${p.id_puesto}`}>
                          {p.nombre_puesto}
                        </label>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mb-4">
                <label className="form-label" style={labelStyle}>Licencias</label>
                {licencias.length === 0 && (
                  <div className="mb-2" style={{color: '#A0B2C6', fontSize: '14px'}}>Sin licencias registradas.</div>
                )}
                {licencias.map((fila) => {
                  const vencida = fila.fecha_vencimiento && fila.fecha_vencimiento < hoyISO();
                  return (
                    <div className="row g-2 mb-2 align-items-end" key={fila.clave}>
                      <div className="col-md-4">
                        <small style={{color: '#A0B2C6'}}>Tipo</small>
                        <select
                          className="form-select up-input"
                          value={fila.id_tipo_licencia}
                          onChange={(e) => cambiarLicencia(fila.clave, 'id_tipo_licencia', e.target.value)}
                          required
                        >
                          <option value="">Selecciona...</option>
                          {catalogo.tiposLicencia
                            .filter((t) => String(t.id_tipo_licencia) === fila.id_tipo_licencia
                              || !licencias.some((l) => l.id_tipo_licencia === String(t.id_tipo_licencia)))
                            .map((t) => (
                              <option key={t.id_tipo_licencia} value={t.id_tipo_licencia}>{t.nombre_licencia}</option>
                            ))}
                        </select>
                      </div>
                      <div className="col-md-3">
                        <small style={{color: '#A0B2C6'}}>Emisión</small>
                        <input
                          type="date"
                          className="form-control up-input"
                          value={fila.fecha_emision}
                          onChange={(e) => cambiarLicencia(fila.clave, 'fecha_emision', e.target.value)}
                          required
                        />
                      </div>
                      <div className="col-md-3">
                        <small style={{color: vencida ? '#F2867D' : '#A0B2C6'}}>
                          Vencimiento{vencida && ' (vencida)'}
                        </small>
                        <input
                          type="date"
                          className="form-control up-input"
                          style={vencida ? {borderColor: '#E2574C'} : undefined}
                          value={fila.fecha_vencimiento}
                          min={fila.fecha_emision || undefined}
                          onChange={(e) => cambiarLicencia(fila.clave, 'fecha_vencimiento', e.target.value)}
                          required
                        />
                      </div>
                      <div className="col-md-2">
                        <button type="button" className="btn-secondary w-100" onClick={() => quitarLicencia(fila.clave)}>
                          <i className="bi bi-trash"></i> Quitar
                        </button>
                      </div>
                    </div>
                  );
                })}
                <button
                  type="button"
                  className="btn-secondary mt-1"
                  onClick={agregarLicencia}
                  disabled={licencias.length >= catalogo.tiposLicencia.length}
                >
                  <i className="bi bi-plus-lg"></i> Agregar licencia
                </button>
              </div>

              <div className="mb-4">
                <label className="form-label" style={labelStyle}>Maquinaria certificada</label>
                {maquinarias.length === 0 && (
                  <div className="mb-2" style={{color: '#A0B2C6', fontSize: '14px'}}>Sin certificaciones registradas.</div>
                )}
                {maquinarias.map((fila) => {
                  const vencida = fila.fecha_vencimiento && fila.fecha_vencimiento < hoyISO();
                  const aviso = avisoLicenciaRequerida(fila);
                  return (
                    <div className="mb-2" key={fila.clave}>
                      <div className="row g-2 align-items-end">
                        <div className="col-md-5">
                          <small style={{color: '#A0B2C6'}}>Máquina</small>
                          <select
                            className="form-select up-input"
                            value={fila.id_maquinaria}
                            onChange={(e) => cambiarMaquinaria(fila.clave, 'id_maquinaria', e.target.value)}
                            required
                          >
                            <option value="">Selecciona...</option>
                            {catalogo.maquinarias
                              .filter((m) => String(m.id_maquinaria) === fila.id_maquinaria
                                || !maquinarias.some((f) => f.id_maquinaria === String(m.id_maquinaria)))
                              .map((m) => (
                                <option key={m.id_maquinaria} value={m.id_maquinaria}>{m.nombre_maquinaria}</option>
                              ))}
                          </select>
                        </div>
                        <div className="col-md-5">
                          <small style={{color: vencida ? '#F2867D' : '#A0B2C6'}}>
                            Vencimiento (opcional){vencida && ' (vencida)'}
                          </small>
                          <input
                            type="date"
                            className="form-control up-input"
                            style={vencida ? {borderColor: '#E2574C'} : undefined}
                            value={fila.fecha_vencimiento}
                            onChange={(e) => cambiarMaquinaria(fila.clave, 'fecha_vencimiento', e.target.value)}
                          />
                        </div>
                        <div className="col-md-2">
                          <button type="button" className="btn-secondary w-100" onClick={() => quitarMaquinaria(fila.clave)}>
                            <i className="bi bi-trash"></i> Quitar
                          </button>
                        </div>
                      </div>
                      {aviso && (
                        <div className="mt-1" style={{color: '#F2A63D', fontSize: '13px'}}>
                          <i className="bi bi-exclamation-triangle me-1"></i>{aviso}
                        </div>
                      )}
                    </div>
                  );
                })}
                <button
                  type="button"
                  className="btn-secondary mt-1"
                  onClick={agregarMaquinaria}
                  disabled={maquinarias.length >= catalogo.maquinarias.length}
                >
                  <i className="bi bi-plus-lg"></i> Agregar máquina
                </button>
              </div>
              <hr style={{borderColor: '#1E3349', margin: '40px 0 20px'}} />
              <div className="d-flex justify-content-end gap-3 mt-4">
                <button type="button" onClick={() => navigate('/usuarios')} className="btn-secondary">
                  Cancelar
                </button>
                <BotonCargando
                  type="submit"
                  className="btn-primary"
                  cargando={guardando}
                  textoCargando={esModoEdicion ? 'Guardando...' : 'Creando...'}
                >
                  {esModoEdicion ? 'Guardar Cambios' : 'Crear Usuario'}
                </BotonCargando>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
export default FormularioUsuario;