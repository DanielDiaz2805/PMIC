// api.js - Comunicación HTTP con el Backend
// Diagrama Nivel 1: flecha HTTP Request/Response

import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// POST /api/procesar
export async function iniciarProcesamiento(urls, workers) {
  const res = await api.post("/api/procesar", { urls, workers });
  return res.data;
}

// GET /api/estado/{proceso_id}
export async function obtenerEstado(procesoId) {
  const res = await api.get(`/api/estado/${procesoId}`);
  return res.data;
}