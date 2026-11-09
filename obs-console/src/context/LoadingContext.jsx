import React, { createContext, useContext, useState, useCallback } from 'react';

const LoadingContext = createContext();

export const useLoading = () => useContext(LoadingContext);

export const LoadingProvider = ({ children }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');

  const showLoading = useCallback((message = '') => {
    setLoadingMessage(message);
    setIsLoading(true);
  }, []);

  const hideLoading = useCallback(() => {
    setIsLoading(false);
    setLoadingMessage('');
  }, []);

  const value = { isLoading, loadingMessage, showLoading, hideLoading };

  return (
    <LoadingContext.Provider value={value}>
      {children}
      {isLoading && <GlobalLoadingSpinner message={loadingMessage} />}
    </LoadingContext.Provider>
  );
};

const GlobalLoadingSpinner = ({ message }) => (
  <>
    <style>{`
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `}</style>
    <div style={overlayStyles}>
      <div style={panelStyles}>
        <div style={spinnerStyles}></div>
        {message ? <p style={messageStyles}>{message}</p> : null}
      </div>
    </div>
  </>
);

const overlayStyles = {
  position: "fixed",
  top: 0,
  left: 0,
  width: "100%",
  height: "100%",
  backgroundColor: "rgba(0, 0, 0, 0.5)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  zIndex: 1000,
};

const panelStyles = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "16px",
};

const spinnerStyles = {
  border: "16px solid #f3f3f3",
  borderTop: "16px solid #3498db",
  borderRadius: "50%",
  width: "120px",
  height: "120px",
  animation: "spin 2s linear infinite",
};

const messageStyles = {
  color: "#fff",
  fontSize: "1.1rem",
  textAlign: "center",
  maxWidth: "420px",
  margin: 0,
};
