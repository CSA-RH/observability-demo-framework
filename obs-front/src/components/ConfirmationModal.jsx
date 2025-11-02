// ConfirmationModal.jsx (Ensure this is the latest version)

import React from 'react';
import ReactDOM from 'react-dom';

function ConfirmationModal({
  show,
  onHide,
  onConfirm,
  title,
  body,
  confirmText = "Confirm",
  cancelText = "Cancel",
  confirmClass = "btn-primary" 
}) {
  
  const handleBackdropClick = (e) => {
    e.stopPropagation();
    console.debug("Backdrop click ignored (static behavior).");
  };

  if (!show) {
    return null;
  }

  // The 'fade' class controls the animation. We add 'show' only when needed.
  const modalContent = (
    <div
      className={`modal fade ${show ? 'show' : ''}`}
      // Use inline style to manually set 'display: block' 
      // as the 'show' class often doesn't do this alone without Bootstrap JS
      style={{ display: 'block' }} 
      tabIndex="-1"
      role="dialog"
      aria-labelledby="confirmationModalTitle"
      aria-modal="true"
    >
      {/* 1. BACKDROP (z-index 1050 via custom CSS) */}
      <div 
        className="modal-backdrop fade show" 
        onClick={handleBackdropClick}
      ></div>
      
      {/* 2. DIALOG CONTENT (z-index 1060 via custom CSS) */}
      <div className="modal-dialog modal-dialog-centered" role="document">
        <div className="modal-content">

          {/* Header */}
          <div className="modal-header">
            <h5 className="modal-title" id="confirmationModalTitle">{title}</h5>
            <button 
              type="button" 
              className="btn-close" 
              aria-label="Close" 
              onClick={onHide}
            ></button>
          </div>

          {/* Body */}
          <div className="modal-body">
            <p>{body}</p>
          </div>

          {/* Footer with Action Buttons */}
          <div className="modal-footer">
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={onHide}
            >
              {cancelText}
            </button>
            <button 
              type="button" 
              className={`btn ${confirmClass}`} 
              onClick={onConfirm}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(
    modalContent,
    document.getElementById('modal-root')
  );
}

export default ConfirmationModal;