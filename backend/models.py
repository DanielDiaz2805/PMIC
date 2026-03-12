

import threading
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────
# ESTADOS DEL PROCESO
# ─────────────────────────────────────────────
# Exactamente los 4 estados que pide el taller
# y que aparecen en el diagrama Nivel 2

class EstadoProceso(Enum):
    EN_PROCESO              = "EN_PROCESO"
    COMPLETADO              = "COMPLETADO"
    COMPLETADO_CON_ERRORES  = "COMPLETADO_CON_ERRORES"
    FALLIDO                 = "FALLIDO"


# ─────────────────────────────────────────────
# MÉTRICAS POR ETAPA
# ─────────────────────────────────────────────
# Una instancia de esta clase por cada etapa:
# Descarga, Redimensionamiento, Conversión, Marca de Agua

class MetricasEtapa:
    def __init__(self, nombre: str):
        self.nombre                 = nombre   # Ej: "Descarga"
        self.total_procesados       = 0        # Cuántas imágenes procesó
        self.total_fallidos         = 0        # Cuántas fallaron
        self.tiempo_total           = 0.0      # Suma de todos los tiempos
        self.tiempos_individuales   = []       # Lista de tiempos por imagen

    @property
    def tiempo_promedio(self) -> float:
        """Tiempo promedio por imagen en esta etapa"""
        if self.total_procesados == 0:
            return 0.0
        return self.tiempo_total / self.total_procesados

    def registrar_exito(self, tiempo: float, worker: str):
        """
        Un worker llama esto cuando termina de procesar
        una imagen exitosamente.
        """
        self.total_procesados += 1
        self.tiempo_total     += tiempo
        self.tiempos_individuales.append({
            "tiempo": tiempo,
            "worker": worker
        })

    def registrar_fallo(self, worker: str, error: str):
        """
        Un worker llama esto cuando falla al procesar
        una imagen.
        """
        self.total_fallidos += 1
        self.tiempos_individuales.append({
            "tiempo": 0,
            "worker": worker,
            "error": error
        })

    def to_dict(self) -> dict:
        """Convierte las métricas a diccionario para la API"""
        return {
            "etapa":              self.nombre,
            "total_procesados":   self.total_procesados,
            "total_fallidos":     self.total_fallidos,
            "tiempo_total":       round(self.tiempo_total, 3),
            "tiempo_promedio":    round(self.tiempo_promedio, 3),
        }


# ─────────────────────────────────────────────
# REGISTRO PRINCIPAL DEL PROCESO
# ─────────────────────────────────────────────
# Una instancia por cada proceso iniciado por el usuario.
# Se identifica por su proceso_id (UUID).

class RegistroProceso:
    def __init__(self, proceso_id: str, total_imagenes: int):
        # Identificación
        self.proceso_id         = proceso_id
        self.total_imagenes     = total_imagenes

        # Estado
        self.estado             = EstadoProceso.EN_PROCESO

        # Tiempos
        self.fecha_inicio       = datetime.now()
        self.fecha_fin          = None

        # Métricas por etapa — una por cada caja del diagrama
        self.descarga           = MetricasEtapa("Descarga")
        self.redimensionamiento = MetricasEtapa("Redimensionamiento")
        self.conversion         = MetricasEtapa("Conversion")
        self.marca_agua         = MetricasEtapa("MarcaAgua")

        # Lock para escritura segura desde múltiples workers
        # Esto evita condiciones de carrera cuando varios
        # workers actualizan las métricas al mismo tiempo
        self._lock              = threading.Lock()

    @property
    def tiempo_total_ejecucion(self) -> float:
        """Tiempo total del proceso en segundos"""
        if self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).total_seconds()
        return (datetime.now() - self.fecha_inicio).total_seconds()

    @property
    def total_fallidos(self) -> int:
        """Total de imágenes con error en todo el pipeline"""
        return (
            self.descarga.total_fallidos +
            self.redimensionamiento.total_fallidos +
            self.conversion.total_fallidos +
            self.marca_agua.total_fallidos
        )

    @property
    def porcentaje_exito(self) -> float:
        """% de imágenes procesadas exitosamente"""
        if self.total_imagenes == 0:
            return 0.0
        exitosas = self.marca_agua.total_procesados
        return round((exitosas / self.total_imagenes) * 100, 2)

    @property
    def porcentaje_fallo(self) -> float:
        """% de imágenes que fallaron"""
        return round(100 - self.porcentaje_exito, 2)

    def actualizar_estado(self):
        """
        Revisa el estado del proceso y lo actualiza.
        Se llama cuando el pipeline termina.
        """
        with self._lock:
            self.fecha_fin = datetime.now()
            if self.total_fallidos == 0:
                self.estado = EstadoProceso.COMPLETADO
            elif self.total_fallidos < self.total_imagenes:
                self.estado = EstadoProceso.COMPLETADO_CON_ERRORES
            else:
                self.estado = EstadoProceso.FALLIDO

    def to_dict(self) -> dict:
        """
        Convierte todo el registro a diccionario.
        Esto es lo que retorna el endpoint GET /api/estado/{id}
        """
        return {
            # Información General
            "proceso_id":               self.proceso_id,
            "estado":                   self.estado.value,
            "fecha_inicio":             self.fecha_inicio.isoformat(),
            "fecha_fin":                self.fecha_fin.isoformat() if self.fecha_fin else None,
            "tiempo_total_ejecucion":   round(self.tiempo_total_ejecucion, 3),

            # Métricas por Etapa
            "metricas_etapas": {
                "descarga":             self.descarga.to_dict(),
                "redimensionamiento":   self.redimensionamiento.to_dict(),
                "conversion":           self.conversion.to_dict(),
                "marca_agua":           self.marca_agua.to_dict(),
            },

            # Resumen Global
            "resumen": {
                "total_imagenes":       self.total_imagenes,
                "total_fallidos":       self.total_fallidos,
                "porcentaje_exito":     self.porcentaje_exito,
                "porcentaje_fallo":     self.porcentaje_fallo,
            }
        }


# ─────────────────────────────────────────────
# ALMACÉN GLOBAL DE PROCESOS
# ─────────────────────────────────────────────
# Diccionario en memoria donde guardamos todos
# los procesos activos e históricos.
# La API consulta aquí con el proceso_id.

procesos: dict[str, RegistroProceso] = {}
_lock_procesos = threading.Lock()


def crear_proceso(proceso_id: str, total_imagenes: int) -> RegistroProceso:
    """Crea un nuevo registro de proceso y lo guarda"""
    with _lock_procesos:
        proceso = RegistroProceso(proceso_id, total_imagenes)
        procesos[proceso_id] = proceso
        return proceso


def obtener_proceso(proceso_id: str) -> RegistroProceso | None:
    """Busca un proceso por su ID. Retorna None si no existe"""
    return procesos.get(proceso_id)