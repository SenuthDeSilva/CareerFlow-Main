import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Results from './pages/Results';
import Jobs from './pages/Jobs';
import Explain from './pages/Explain';
import Scraping from './pages/Scraping';
import DatabasePage from './pages/Database';
import Analytics from './pages/Analytics';
import Bookmarks from './pages/Bookmarks';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"          element={<Dashboard />} />
          <Route path="upload"             element={<Upload />} />
          <Route path="results/:resumeId"  element={<Results />} />
          <Route path="explain/:resumeId"  element={<Explain />} />
          <Route path="jobs"               element={<Jobs />} />
          <Route path="scraping"           element={<Scraping />} />
          <Route path="database"           element={<DatabasePage />} />
          <Route path="analytics"          element={<Analytics />} />
          <Route path="bookmarks"          element={<Bookmarks />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;