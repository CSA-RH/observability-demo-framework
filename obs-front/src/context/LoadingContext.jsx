import React, { createContext, useContext, useState, useCallback } from 'react';

// 1. Create the context
const LoadingContext = createContext();

// 2. Create a custom hook for easy access
export const useLoading = () => useContext(LoadingContext);

// 3. Create the Provider component
export const LoadingProvider = ({ children }) => {
  const [isLoading, setIsLoading] = useState(false);

  // Use useCallback to prevent unnecessary re-renders
  const showLoading = useCallback(() => setIsLoading(true), []);
  const hideLoading = useCallback(() => setIsLoading(false), []);

  const value = { isLoading, showLoading, hideLoading };

  return (
    <LoadingContext.Provider value={value}>
      {children}
      {isLoading && <GlobalLoadingSpinner />}
    </LoadingContext.Provider>
  );
};

// 4. Co-locate the Spinner component and its styles here
const GlobalLoadingSpinner = () => (
  <>
    {/* This <style> tag injects the animation safely */}
    <style>{`
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `}</style>
    <div style={overlayStyles}>
      <div style={spinnerStyles}></div>
    </div>
  </>
);

// Styles for the overlay and spinner
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
    zIndex: 1000, // Ensure it overlays everything
};

const spinnerStyles = {
    border: "16px solid #f3f3f3", // Light gray
    borderTop: "16px solid #3498db", // Blue
    borderRadius: "50%",
    width: "120px",
    height: "120px",
    animation: "spin 2s linear infinite",
};