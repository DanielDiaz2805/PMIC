"""
main.py - API REST del Sistema PMIC
Diagrama Nivel 1: caja Backend - API REST
Diagrama Nivel 2: caja azul API REST FastAPI

Endpoints:
  POST /api/procesar      -> recibe URLs + workers -> retorna proceso_id
  GET  /api/estado/{id}   -> consulta metricas     -> retorna estado
  GET  /api/db/{id}       -> consulta base de datos -> retorna metadatos completos
"""

import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional
from models import crear_proceso, obtener_proceso
from pipeline import iniciar_pipeline_async
from database import inicializar_db, guardar_proceso, actualizar_estado_proceso, consultar_metadatos_proceso

app = FastAPI(
    title       = "PMIC - Plataforma de Procesamiento Masivo de Imagenes",
    description = "Pipeline concurrente con patron Productor-Consumidor",
    version     = "1.0.0"
)

# Inicializar base de datos al arrancar el servidor
inicializar_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────
# MODELOS DE ENTRADA
# ─────────────────────────────────────────────

class ConfigWorkers(BaseModel):
    descarga:           int = 2
    redimensionamiento: int = 2
    conversion:         int = 2
    marca_agua:         int = 2

    @field_validator("descarga", "redimensionamiento", "conversion", "marca_agua")
    @classmethod
    def validar_workers(cls, v):
        if v < 1:
            raise ValueError("Minimo 1 worker por etapa")
        if v > 10:
            raise ValueError("Maximo 10 workers por etapa")
        return v


class SolicitudProcesamiento(BaseModel):
    urls:    list[str]
    workers: Optional[ConfigWorkers] = ConfigWorkers()

    @field_validator("urls")
    @classmethod
    def validar_urls(cls, v):
        if len(v) == 0:
            raise ValueError("Debe enviar al menos una URL")
        if len(v) > 50:
            raise ValueError("Maximo 50 URLs por proceso")
        return v


# ─────────────────────────────────────────────
# ENDPOINT 1: POST /api/procesar
# ─────────────────────────────────────────────

@app.post("/api/procesar")
async def iniciar_procesamiento(solicitud: SolicitudProcesamiento):
    proceso_id = str(uuid.uuid4())

    # Registrar en memoria
    crear_proceso(
        proceso_id     = proceso_id,
        total_imagenes = len(solicitud.urls)
    )

    # Registrar en base de datos
    guardar_proceso(
        proceso_id = proceso_id,
        total_urls = len(solicitud.urls)
    )

    config_workers = {
        "descarga":           solicitud.workers.descarga,
        "redimensionamiento": solicitud.workers.redimensionamiento,
        "conversion":         solicitud.workers.conversion,
        "marca_agua":         solicitud.workers.marca_agua,
    }

    iniciar_pipeline_async(
        proceso_id     = proceso_id,
        urls           = solicitud.urls,
        config_workers = config_workers
    )

    return {
        "proceso_id":     proceso_id,
        "mensaje":        "Pipeline iniciado correctamente",
        "total_imagenes": len(solicitud.urls),
        "workers":        config_workers
    }


# ─────────────────────────────────────────────
# ENDPOINT 2: GET /api/estado/{proceso_id}
# ─────────────────────────────────────────────

@app.get("/api/estado/{proceso_id}")
async def obtener_estado(proceso_id: str):
    proceso = obtener_proceso(proceso_id)
    if not proceso:
        raise HTTPException(status_code=404, detail=f"Proceso {proceso_id} no encontrado")

    # Actualizar estado en base de datos
    actualizar_estado_proceso(proceso_id, proceso.estado.value)

    return proceso.to_dict()


# ─────────────────────────────────────────────
# ENDPOINT 3: GET /api/db/{proceso_id}
# ─────────────────────────────────────────────

@app.get("/api/db/{proceso_id}")
async def obtener_metadatos_db(proceso_id: str):
    """
    Retorna todos los metadatos guardados en SQLite para un proceso.
    Muestra exactamente qué worker procesó cada imagen y cuándo.
    """
    datos = consultar_metadatos_proceso(proceso_id)
    return datos


# ─────────────────────────────────────────────
# ENDPOINT ADICIONAL: GET /
# ─────────────────────────────────────────────

@app.get("/")
async def raiz():
    return {
        "sistema":   "PMIC",
        "version":   "1.0.0",
        "estado":    "activo",
        "endpoints": [
            "POST /api/procesar",
            "GET  /api/estado/{proceso_id}",
            "GET  /api/db/{proceso_id}"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)