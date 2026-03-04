// Dashboard.jsx - Visualización de Métricas en Tiempo Real
// Diagrama Nivel 2: consume GET /api/estado/{id}
export default function Dashboard({ estado }) {
  if (!estado) return null;
  const { resumen, metricas_etapas, tiempo_total_ejecucion } = estado;
  const colorEstado = {
    EN_PROCESO:             "bg-yellow-100 text-yellow-800",
    COMPLETADO:             "bg-green-100  text-green-800",
    COMPLETADO_CON_ERRORES: "bg-orange-100 text-orange-800",
    FALLIDO:                "bg-red-100    text-red-800",
  };
  const etapas = [
    { key: "descarga",           label: "⬇️ Descarga",          color: "border-green-400  bg-green-50"  },
    { key: "redimensionamiento", label: "↔️ Redimensionamiento", color: "border-purple-400 bg-purple-50" },
    { key: "conversion",         label: "🔄 Conversión",         color: "border-orange-400 bg-orange-50" },
    { key: "marca_agua",         label: "💧 Marca de Agua",      color: "border-red-400    bg-red-50"    },
  ];
  return (
    <div className="mt-8 space-y-6">

      {/* Resumen general */}
      <div className="bg-white rounded-2xl shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">Estado del Proceso</h2>
          <span className={`px-4 py-1 rounded-full font-semibold text-sm ${colorEstado[estado.estado]}`}>
            {estado.estado}
          </span>
        </div>

        {/* Tarjetas de resumen */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card label="Total Imágenes" value={resumen.total_imagenes}         color="blue"   />
          <Card label="Fallidas"        value={resumen.total_fallidos}         color="red"    />
          <Card label="% Éxito"         value={`${resumen.porcentaje_exito}%`} color="green"  />
          <Card label="Tiempo Total"    value={`${tiempo_total_ejecucion}s`}   color="purple" />
        </div>

        {/* Fechas de inicio y fin */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="bg-gray-50 rounded-xl border p-3">
            <p className="text-gray-500 font-medium">🕐 Fecha de Inicio</p>
            <p className="font-bold text-gray-800 mt-1">
              {new Date(estado.fecha_inicio).toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-50 rounded-xl border p-3">
            <p className="text-gray-500 font-medium">🏁 Fecha de Finalización</p>
            <p className="font-bold text-gray-800 mt-1">
              {estado.fecha_fin
                ? new Date(estado.fecha_fin).toLocaleString()
                : <span className="text-yellow-600 animate-pulse">En progreso...</span>
              }
            </p>
          </div>
        </div>
      </div>

      {/* Métricas por etapa */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {etapas.map(({ key, label, color }) => {
          const etapa = metricas_etapas[key];
          if (!etapa) return null;
          return (
            <div key={key} className={`rounded-2xl border-2 shadow p-5 ${color}`}>
              <h3 className="font-bold text-gray-700 mb-3">{label}</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-gray-500">Procesadas</p>
                  <p className="font-bold text-lg">{etapa.total_procesados}</p>
                </div>
                <div>
                  <p className="text-gray-500">Fallidas</p>
                  <p className="font-bold text-lg text-red-600">{etapa.total_fallidos}</p>
                </div>
                <div>
                  <p className="text-gray-500">Tiempo total</p>
                  <p className="font-bold text-lg">{etapa.tiempo_total}s</p>
                </div>
                <div>
                  <p className="text-gray-500">T. promedio</p>
                  <p className="font-bold text-lg">{etapa.tiempo_promedio}s</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}

function Card({ label, value, color }) {
  const colors = {
    blue:   "bg-blue-50   text-blue-700",
    red:    "bg-red-50    text-red-700",
    green:  "bg-green-50  text-green-700",
    purple: "bg-purple-50 text-purple-700",
  };
  return (
    <div className={`rounded-xl border p-4 text-center ${colors[color]}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-1 font-medium">{label}</p>
    </div>
  );
}