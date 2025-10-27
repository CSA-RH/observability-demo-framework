import { toast } from 'react-toastify';
import { IconError, IconSuccess } from '../components/Icons'; // Asumo la ruta de tus iconos

/**
 * Muestra un toast de éxito y lo registra en la consola.
 * @param {string} message - El mensaje a mostrar.
 */
export const notifySuccess = (message) => {
  console.log(message);
  toast.success(message, { icon: <IconSuccess /> });
};

/**
 * Muestra un toast de error y lo registra en la consola.
 * @param {string} message - Un prefijo para el mensaje de error (ej. "Error al crear").
 * @param {Error|string} [error] - El objeto de error o mensaje de error.
 */
export const notifyError = (message, error) => {
  // Construye un mensaje de error detallado
  const errorMessage = error instanceof Error ? error.message : String(error || '');
  const fullMessage = `${message}${errorMessage ? `: ${errorMessage}` : ''}`;
  
  console.error(fullMessage); // Siempre registra el error completo
  toast.error(fullMessage, { icon: <IconError /> });
};