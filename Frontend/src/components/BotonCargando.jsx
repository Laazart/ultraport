/**
 * Botón que, mientras `cargando` es true, queda deshabilitado y muestra un
 * spinner, para evitar dobles envíos.
 *
 * - `textoCargando`: contenido a mostrar junto al spinner (por defecto, los
 *   mismos children). Pasar `null` para mostrar solo el spinner (botones de icono).
 * - El resto de props (className, onClick, type, title...) van al <button>.
 */
const BotonCargando = ({
  cargando = false,
  disabled = false,
  textoCargando,
  type = 'button',
  children,
  ...props
}) => {
  const contenido = textoCargando === undefined ? children : textoCargando;
  return (
    <button {...props} type={type} disabled={disabled || cargando} aria-busy={cargando}>
      {cargando ? (
        <>
          <span
            className={`spinner-border spinner-border-sm${contenido ? ' me-2' : ''}`}
            role="status"
            aria-hidden="true"
          ></span>
          {contenido}
        </>
      ) : (
        children
      )}
    </button>
  );
};

export default BotonCargando;
