import { useState } from 'react';
import './CampoPassword.css';

/**
 * Input de contraseña con un botón de ojo para mostrar u ocultar lo escrito.
 * - `className`: clases del contenedor (p. ej. 'mb-3').
 * - El resto de props (value, onChange, placeholder, disabled...) van al <input>.
 */
const CampoPassword = ({ className = '', disabled, ...props }) => {
  const [visible, setVisible] = useState(false);
  const etiqueta = visible ? 'Ocultar contraseña' : 'Mostrar contraseña';

  return (
    <div className={`campo-password ${className}`.trim()}>
      <input
        className="form-control form-control-lg"
        {...props}
        type={visible ? 'text' : 'password'}
        disabled={disabled}
      />
      <button
        type="button"
        className="btn-ver-password"
        onClick={() => setVisible((v) => !v)}
        disabled={disabled}
        aria-label={etiqueta}
        aria-pressed={visible}
        title={etiqueta}
      >
        <i className={`bi ${visible ? 'bi-eye-slash' : 'bi-eye'}`}></i>
      </button>
    </div>
  );
};

export default CampoPassword;
