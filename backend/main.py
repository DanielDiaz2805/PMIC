"""
main.py - API REST del Sistema PMIC
=====================================
Diagrama Nivel 1: caja Backend - API REST
Diagrama Nivel 2: caja azul API REST FastAPI

Endpoints:
  POST /api/procesar      -> recibe URLs + workers -> retorna proceso_id
  GET  /api/estado/{id}   -> consulta metricas     -> retorna estado
"""

import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
from models import crear_proceso, obtener_proceso
from pipeline import iniciar_pipeline_async


# ─────────────────────────────────────────────
# INICIALIZAR APP
# ─────────────────────────────────────────────

app = FastAPI(
    title       = "PMIC - Plataforma de Procesamiento Masivo de Imagenes",
    description = "Pipeline concurrente con patron Productor-Consumidor",
    version     = "1.0.0"
)

# Permitir peticiones desde el Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────
# MODELOS DE ENTRADA (lo que recibe la API)
# ─────────────────────────────────────────────

class ConfigWorkers(BaseModel):
    """
    Configuracion de workers por etapa.
    El usuario define cuantos workers quiere para cada etapa.
    """
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
    """
    JSON que envia el Frontend al POST /api/procesar

    Ejemplo:
    {
        "urls": [
            "https://example.com/foto1.jpg",
            "https://example.com/foto2.jpg"
        ],
        "workers": {
            "descarga": 3,
            "redimensionamiento": 2,
            "conversion": 2,
            "marca_agua": 2
        }
    }
    """
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
    """
    Diagrama Nivel 2: Actor -> API REST -> Cola de URLs

    1. Recibe las URLs y configuracion de workers
    2. Genera un UUID unico para identificar el proceso
    3. Registra el proceso en el modulo de metricas
    4. Arranca el pipeline en un hilo separado (no bloqueante)
    5. Retorna el proceso_id inmediatamente

    El usuario usa el proceso_id para consultar el estado despues.
    """

    # Generar ID unico para este proceso
    proceso_id = str(uuid.uuid4())

    # Crear registro en el modulo de metricas
    crear_proceso(
        proceso_id     = proceso_id,
        total_imagenes = len(solicitud.urls)
    )

    # Convertir config a diccionario
    config_workers = {
        "descarga":           solicitud.workers.descarga,
        "redimensionamiento": solicitud.workers.redimensionamiento,
        "conversion":         solicitud.workers.conversion,
        "marca_agua":         solicitud.workers.marca_agua,
    }

    # Arrancar pipeline en hilo separado
    # La API NO espera que el pipeline termine
    iniciar_pipeline_async(
        proceso_id    = proceso_id,
        urls          = solicitud.urls,
        config_workers = config_workers
    )

    # Retornar inmediatamente al usuario
    return {
        "proceso_id":      proceso_id,
        "mensaje":         "Pipeline iniciado correctamente",
        "total_imagenes":  len(solicitud.urls),
        "workers":         config_workers
    }


# ─────────────────────────────────────────────
# ENDPOINT 2: GET /api/estado/{proceso_id}
# ─────────────────────────────────────────────

@app.get("/api/estado/{proceso_id}")
async def obtener_estado(proceso_id: str):
    """
    Diagrama Nivel 2: API REST -> Modulo de Metricas

    Consulta el estado actual del pipeline y retorna
    todas las metricas registradas por los workers.

    El Frontend hace polling a este endpoint para
    actualizar el dashboard en tiempo real.
    """

    proceso = obtener_proceso(proceso_id)

    if not proceso:
        raise HTTPException(
            status_code = 404,
            detail      = f"Proceso {proceso_id} no encontrado"
        )

    return proceso.to_dict()


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
            "GET  /api/estado/{proceso_id}"
        ]
    }


# ─────────────────────────────────────────────
# ARRANCAR EL SERVIDOR
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host     = "0.0.0.0",
        port     = 8000,
        reload   = True
    )