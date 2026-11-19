import { useEffect, useId, useRef } from 'react';
import BotonCargando from './BotonCargando';
import './ModalConfirmacion.css';

/**
 * Diálogo de confirmación con el estilo de la app (reemplaza window.confirm).
 * Cancelar, Esc o clic fuera cierran sin hacer nada; el foco inicial va a
 * Cancelar para que Enter no confirme por accidente.
 *
 * variante: 'aprobar' | 'rechazar' | 'neutral' (color del botón e ícono).
 */
const ICONOS = {
  aprobar: 'bi-check-circle',
  rechazar: 'bi-x-octagon',
  neutral: 'bi-question-circle',
};

const ModalConfirmacion = ({
  abierto,
  titulo,
  mensaje,
  textoConfirmar = 'Confirmar',
  textoCancelar = 'Cancelar',
  variante = 'neutral',
  cargando = false,
  onConfirmar,
  onCancelar,
}) => {
  const idTitulo = useId();
  const cancelarRef = useRef(null);

  useEffect(() => {
    if (!abierto) return undefined;
    cancelarRef.current?.focus();
    const alPresionar = (e) => {
      if (e.key === 'Escape' && !cargando) onCancelar();
    };
    document.addEventListener('keydown', alPresionar);
    return () => document.removeEventListener('keydown', alPresionar);
  }, [abierto, cargando, onCancelar]);

  if (!abierto) return null;

  return (
    <div
      className="up-confirm-overlay"
      onClick={(e) => e.target === e.currentTarget && !cargando && onCancelar()}
    >
      <div className="up-confirm" role="dialog" aria-modal="true" aria-labelledby={idTitulo}>
        <div className={`up-confirm-icono ${variante}`}>
          <i className={`bi ${ICONOS[variante] ?? ICONOS.neutral}`}></i>
        </div>
        <h4 id={idTitulo} className="up-confirm-titulo">{titulo}</h4>
        {mensaje && <p className="up-confirm-mensaje">{mensaje}</p>}
        <div className="up-confirm-acciones">
          <button
            ref={cancelarRef}
            type="button"
            className="up-confirm-btn cancelar"
            onClick={onCancelar}
            disabled={cargando}
          >
            {textoCancelar}
          </button>
          <BotonCargando
            type="button"
            className={`up-confirm-btn confirmar ${variante}`}
            cargando={cargando}
            textoCargando="Guardando..."
            onClick={onConfirmar}
          >
            {textoConfirmar}
          </BotonCargando>
        </div>
      </div>
    </div>
  );
};

export default ModalConfirmacion;
