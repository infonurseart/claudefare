import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
if ('serviceWorker' in navigator) { window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(error => console.warn('No se pudo registrar la PWA', error))); }
ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
