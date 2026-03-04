// App.jsx - Componente Principal
// Diagrama Nivel 1: caja "Frontend - React + Vite"

import { useState, useEffect, useRef } from "react";
import { iniciarProcesamiento, obtenerEstado } from "./api";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [urlsTexto, setUrlsTexto]  = useState("");
  const [workers, setWorkers]      = useState({
    descarga: 2, redimensionamiento: 2, conversion: 2, marca_agua: 2
  });
  const [procesoId, setProcesoId]  = useState(null);
  const [estadoProceso, setEstado] = useState(null);
  const [cargando, setCargando]    = useState(false);
  const [error, setError]          = useState(null);
  const intervaloRef               = useRef(null);

  // Polling cada 2 segundos mientras el proceso corre
  useEffect(() => {
    if (!procesoId) return;
    consultarEstado(procesoId);
    intervaloRef.current = setInterval(() => consultarEstado(procesoId), 2000);
    return () => clearInterval(intervaloRef.current);
  }, [procesoId]);

  // Detener polling cuando termina
  useEffect(() => {
    if (!estadoProceso) return;
    const terminados = ["COMPLETADO", "COMPLETADO_CON_ERRORES", "FALLIDO"];
    if (terminados.includes(estadoProceso.estado)) {
      clearInterval(intervaloRef.current);
    }
  }, [estadoProceso]);

  async function consultarEstado(id) {
    try { setEstado(await obtenerEstado(id)); }
    catch (e) { console.error(e); }
  }

  async function handleEnviar() {
    setError(null);
    const urls = urlsTexto.split("\n").map(u => u.trim()).filter(u => u.length > 0);
    if (urls.length === 0) { setError("Ingresa al menos una URL"); return; }
    try {
      setCargando(true);
      const res = await iniciarProcesamiento(urls, workers);
      setProcesoId(res.proceso_id);
      setEstado(null);
    } catch (e) {
      setError(e.response?.data?.detail || "Error al conectar con el backend");
    } finally { setCargando(false); }
  }

  function handleReset() {
    clearInterval(intervaloRef.current);
    setProcesoId(null); setEstado(null); setError(null); setUrlsTexto("");
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="bg-white rounded-2xl shadow p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800">🖼️ PMIC</h1>
          <p className="text-gray-500 mt-1">
            Plataforma de Procesamiento Masivo de Imágenes Concurrente
          </p>
        </div>

        {/* Formulario */}
        <div className="bg-white rounded-2xl shadow p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-700 mb-4">1. URLs de Imágenes</h2>
          <textarea
            className="w-full border rounded-xl p-3 text-sm font-mono h-32 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder={"https://example.com/foto1.jpg\nhttps://example.com/foto2.jpg"}
            value={urlsTexto}
            onChange={e => setUrlsTexto(e.target.value)}
          />

          <h2 className="text-xl font-bold text-gray-700 mt-6 mb-4">2. Configurar Workers</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(workers).map(([etapa, valor]) => (
              <div key={etapa}>
                <label className="text-sm text-gray-600 capitalize block mb-1">
                  {etapa.replace("_", " ")}
                </label>
                <input
                  type="number" min={1} max={10} value={valor}
                  onChange={e => setWorkers(prev => ({ ...prev, [etapa]: parseInt(e.target.value) || 1 }))}
                  className="w-full border rounded-lg p-2 text-center font-bold focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            ))}
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              ❌ {error}
            </div>
          )}

          <div className="mt-6 flex gap-3">
            <button
              onClick={handleEnviar} disabled={cargando}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold py-3 rounded-xl transition"
            >
              {cargando ? "Enviando..." : "🚀 Iniciar Procesamiento"}
            </button>
            {procesoId && (
              <button onClick={handleReset}
                className="px-6 bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold py-3 rounded-xl transition">
                🔄 Nuevo
              </button>
            )}
          </div>
        </div>

        {/* Proceso ID */}
        {procesoId && (
          <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-4 text-sm">
            <span className="text-blue-600 font-bold">Proceso ID: </span>
            <span className="font-mono text-blue-800">{procesoId}</span>
            {estadoProceso?.estado === "EN_PROCESO" && (
              <span className="ml-3 text-yellow-600 font-semibold animate-pulse">
                ⏳ Procesando...
              </span>
            )}
          </div>
        )}

        {/* Dashboard de métricas */}
        <Dashboard estado={estadoProceso} />

      </div>
    </div>
  );
}