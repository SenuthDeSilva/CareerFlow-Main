import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found. Make sure public/index.html has <div id="root"></div>');
}

const root = ReactDOM.createRoot(container);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);