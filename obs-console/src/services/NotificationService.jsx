import { toast } from 'react-toastify';
import { IconError, IconSuccess } from '../components/Icons'; 

/**
 * Show a success toast with a message. 
 * @param {string} message 
 */
export const notifySuccess = (message) => {
  console.log(message);
  toast.success(message, { icon: <IconSuccess /> });
};

/**
 * Show a toast error
 * @param {string} message - message
 * @param {Error|string} [error] - error exception (optional)
 */
export const notifyError = (message, error) => {
  const errorMessage = error instanceof Error ? error.message : String(error || '');
  const fullMessage = `${message}${errorMessage ? `: ${errorMessage}` : ''}`;
  
  console.error(fullMessage); 
  toast.error(fullMessage, { icon: <IconError /> });
};