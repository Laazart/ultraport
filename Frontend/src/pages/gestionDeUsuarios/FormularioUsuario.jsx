import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import userService, { contratoService } from '../../services/userService';
import './GestionDeUsuarios.css'; 
import { validarRut } from '../../services/tools'

const FormularioUsuario = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const esModoEdicion = Boolean(id);
  const [contratos, setContratos] = useState([]);

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
        setError('No se pudieron cargar los contratos.');
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
  
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(esModoEdicion); 

  useEffect(() => {
    if (esModoEdicion) {
      cargarDatosUsuario(id);
    }
  }, [id, esModoEdicion]);

  const cargarDatosUsuario = async (userId) => {
    try {
      const data = await userService.getUsuarioById(userId);
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
      setError("No se pudo cargar la información del usuario.");
    } finally {
      setCargando(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleGuardar = async (e) => {
    e.preventDefault();
    setError(null);
    if (!validarRut(formData.rut)) {
      setError("El RUT ingresado no es válido. Verifica que esté correcto.");
      return; 
    }
    const datosAEnviar = { ...formData, id_contrato: formData.id_contrato ? Number(formData.id_contrato): null};
    if (esModoEdicion && !datosAEnviar.password) {
      delete datosAEnviar.password;
    }
    if (datosAEnviar.id_rol === '') datosAEnviar.id_rol = null;

    try {
      if (esModoEdicion) {
        await userService.actualizarUsuario(id, datosAEnviar);
        alert("Usuario actualizado correctamente.");
      } else {
        await userService.crearUsuario(datosAEnviar);
        alert("Usuario creado exitosamente.");
      }
      navigate('/usuarios');
    } catch (error) {
      console.error("Error al guardar:", error.response?.data);
      const errorMsg = error.response?.data 
        ? Object.values(error.response.data).flat().join(' ') 
        : "Hubo un error al procesar la solicitud. Revisa los datos.";
      setError(errorMsg);
    }
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
          <span className="sub">Panel de Turnos</span>
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

      <div className="up-dashboard-container" style={{maxWidth: '700px'}}>
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
                      {/*5 Administrador | 7 Encargado de Asignaciones | 6 Trabajador */}
                      <option value="">Selecciona un rol...</option>
                      <option value="1">Administrador</option>
                      <option value="2">Encargado de asignaciones</option>
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
                              {contrato.tipo}
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
                  {/* botones */}
              </div>       
              <hr style={{borderColor: '#1E3349', margin: '40px 0 20px'}} />
              <div className="d-flex justify-content-end gap-3 mt-4">
                <button type="button" onClick={() => navigate('/usuarios')} className="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  {esModoEdicion ? 'Guardar Cambios' : 'Crear Usuario'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
export default FormularioUsuario;