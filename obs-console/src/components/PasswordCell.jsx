import React, { useState } from 'react';
// Assuming you have Bootstrap Icons or Font Awesome linked globally

function PasswordCell({ password }) {
  const [isVisible, setIsVisible] = useState(false);
  const [copyStatus, setCopyStatus] = useState(false);

  const handleToggle = () => {
    setIsVisible(!isVisible);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(password);
      setCopyStatus(true);
      setTimeout(() => setCopyStatus(false), 2000); // Reset status after 2 seconds
    } catch (err) {
      console.error('Failed to copy password: ', err);
      // Optional: setCopyStatus('error');
    }
  };

  return (
    // Outer table cell with the lighter grey background
    <td className="bg-light-gray" style={{ width: '250px' }}>
      <div className="d-flex align-items-center justify-content-between">
        
        {/* Password Display Area - The Medium Gray Box */}
        <div className="bg-med-gray flex-grow-1 me-2" style={{ maxWidth: '160px' }}>
          {isVisible ? (
            <span className="font-monospace text-start d-block">{password}</span>
          ) : (
            // Using read-only input type="password" for the native dot masking
            <input 
              type="password" 
              value={password}
              readOnly
              className="form-control-plaintext p-0 text-center"
              style={{ padding: '0 !important', backgroundColor: 'transparent' }}
            />
          )}
        </div>

        {/* Buttons Group (Small Square Icons) */}
        <div className="btn-group" role="group">
          
          {/* Copy Button */}
          <button 
            className={`btn btn-sm ${copyStatus ? 'btn-success' : 'btn-outline-secondary'}`}
            onClick={handleCopy}
            title={copyStatus ? 'Copied!' : 'Copy to Clipboard'}
            // Custom style to make it a small square for the icon
            style={{ width: '32px', height: '32px', padding: '0' }}
          >
            {/* Icon changes color on success */}
            <i className={copyStatus ? 'bi bi-check-lg' : 'bi bi-clipboard'}></i>
          </button>

          {/* Show/Hide Button */}
          <button 
            className="btn btn-sm btn-outline-secondary ms-1"
            onClick={handleToggle}
            title={isVisible ? 'Hide Password' : 'Show Password'}
            // Custom style to make it a small square for the icon
            style={{ width: '32px', height: '32px', padding: '0' }}
          >
            {/* Icon changes based on state (open eye / crossed-out eye) */}
            <i className={isVisible ? 'bi bi-eye-slash' : 'bi bi-eye'}></i>
          </button>

        </div>
      </div>
    </td>
  );
}

export default PasswordCell;