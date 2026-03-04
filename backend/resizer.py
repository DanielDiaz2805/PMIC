"""
resizer.py - Workers de Redimensionamiento
Diagrama Nivel 2: ETAPA 2 - Cajas moradas (Worker R1, R2...RN)
CONSUMIDOR de Cola Redimensionamiento - PRODUCTOR de Cola Conversion
"""

import time
import queue
import threading
from pathlib import Path
from PIL import Image
from models import RegistroProceso

# Tamano objetivo de redimension
ANCHO_OBJETIVO = 800


class WorkerRedimension(threading.Thread):
    """
    Cada instancia es un hilo independiente.
    Diagrama Nivel 2: caja morada Worker R1, R2...RN

    Ciclo de vida:
    1. Saca imagen de cola_redim        (CONSUMIDOR)
    2. Redimensiona manteniendo aspect ratio
    3. Guarda con sufijo _redimensionado
    4. Mete ruta en cola_conv           (PRODUCTOR)
    5. Repite hasta que no haya mas trabajo
    """

    def __init__(self, nombre, cola_redim, cola_conv, proceso):
        super().__init__(name=nombre, daemon=True)
        self.nombre     = nombre
        self.cola_redim = cola_redim
        self.cola_conv  = cola_conv
        self.proceso    = proceso

    def run(self):
        while True:
            try:
                item = self.cola_redim.get(timeout=5)
            except queue.Empty:
                break
            self._redimensionar(item)
            self.cola_redim.task_done()

    def _redimensionar(self, item):
        inicio = time.time()
        ruta_original = Path(item["ruta"])

        try:
            # Calcular nuevo tamano manteniendo aspect ratio
            # Formula del taller:
            # nuevo_alto = (ancho_objetivo / ancho_original) * alto_original
            with Image.open(ruta_original) as img:
                ancho_original, alto_original = img.size

                # Calcular proporcion
                proporcion   = ANCHO_OBJETIVO / ancho_original
                nuevo_ancho  = ANCHO_OBJETIVO
                nuevo_alto   = int(alto_original * proporcion)

                # Redimensionar con alta calidad
                img_redim = img.resize(
                    (nuevo_ancho, nuevo_alto),
                    Image.LANCZOS
                )

                # Guardar con sufijo _redimensionado
                nombre_nuevo = (
                    ruta_original.stem + "_redimensionado" +
                    ruta_original.suffix
                )
                ruta_nueva = ruta_original.parent / nombre_nuevo
                img_redim.save(ruta_nueva)

            tiempo_proc = round(time.time() - inicio, 3)

            # Registrar en modulo de metricas
            with self.proceso._lock:
                self.proceso.redimensionamiento.registrar_exito(
                    tiempo=tiempo_proc,
                    worker=self.nombre
                )

            print(f"[{self.nombre}] OK: {nombre_nuevo} "
                  f"({ancho_original}x{alto_original} -> "
                  f"{nuevo_ancho}x{nuevo_alto}) en {tiempo_proc}s")

            # Pasar a la siguiente etapa
            self.cola_conv.put({
                **item,
                "ruta":                  str(ruta_nueva),
                "nombre_redimensionado": nombre_nuevo,
                "dimensiones_original":  f"{ancho_original}x{alto_original}",
                "dimensiones_nueva":     f"{nuevo_ancho}x{nuevo_alto}",
                "worker_redimension":    self.nombre,
            })

        except Exception as e:
            tiempo_proc = round(time.time() - inicio, 3)
            print(f"[{self.nombre}] ERROR redimensionando "
                  f"{ruta_original.name}: {e}")
            with self.proceso._lock:
                self.proceso.redimensionamiento.registrar_fallo(
                    worker=self.nombre,
                    error=str(e)
                )


def iniciar_workers_redimension(n_workers, cola_conv, proceso):
    """
    Funcion usada por pipeline.py para arrancar la Etapa 2.
    Crea la Cola de Redimensionamiento y lanza N workers.
    Retorna la cola para que los workers de descarga puedan producir en ella.
    """
    cola_redim = queue.Queue()

    print(f"\nETAPA 2 - REDIMENSIONAMIENTO | Workers: {n_workers}")

    workers = []
    for i in range(1, n_workers + 1):
        worker = WorkerRedimension(
            nombre     = f"Worker-R{i}",
            cola_redim = cola_redim,
            cola_conv  = cola_conv,
            proceso    = proceso
        )
        workers.append(worker)
        worker.start()
        print(f"  Worker-R{i} iniciado")

    return cola_redim, workers