import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

import App from './App.jsx'
import Login from './pages/login/Login'
import Home from './pages/home/Home'
import NotificarInasistencia from './pages/notificarInasistencia/notificarInasistencia'
import MallaDeTurnos from './pages/mallaDeTurnos/mallaDeTurnos'
import GestionDeUsuarios from './pages/gestionDeUsuarios/GestionDeUsuarios'
import ReportesYExportacion from './pages/reportesExportacion/ReportesYExportacion'

import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/login" element={<Login />} />
        <Route path="/home" element={<Home />} />
        <Route path="/notificaciones" element={<NotificarInasistencia />} />
        <Route path="/malla" element={<MallaDeTurnos />} />
        <Route path="/usuarios" element={<GestionDeUsuarios />} />
        <Route path="/reportes" element={<ReportesYExportacion />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
