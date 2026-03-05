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
from database import guardar_metadato_redimension

ANCHO_OBJETIVO = 800


class WorkerRedimension(threading.Thread):
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
        inicio        = time.time()
        ruta_original = Path(item["ruta"])

        try:
            with Image.open(ruta_original) as img:
                ancho_original, alto_original = img.size
                proporcion  = ANCHO_OBJETIVO / ancho_original
                nuevo_ancho = ANCHO_OBJETIVO
                nuevo_alto  = int(alto_original * proporcion)

                img_redim = img.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)

                nombre_nuevo = ruta_original.stem + "_redimensionado" + ruta_original.suffix
                ruta_nueva   = ruta_original.parent / nombre_nuevo
                img_redim.save(ruta_nueva)

            tiempo = round(time.time() - inicio, 3)

            # Guardar en memoria (métricas)
            with self.proceso._lock:
                self.proceso.redimensionamiento.registrar_exito(
                    tiempo=tiempo,
                    worker=self.nombre
                )

            # Guardar en base de datos SQLite
            guardar_metadato_redimension(
                proceso_id     = self.proceso.proceso_id,
                nombre_original = item["nombre_original"],
                nombre_nuevo    = nombre_nuevo,
                tiempo          = tiempo,
                worker          = self.nombre
            )

            print(f"[{self.nombre}] OK: {nombre_nuevo} "
                  f"({ancho_original}x{alto_original} -> "
                  f"{nuevo_ancho}x{nuevo_alto}) en {tiempo}s")

            self.cola_conv.put({
                **item,
                "ruta":                  str(ruta_nueva),
                "nombre_redimensionado": nombre_nuevo,
                "worker_redimension":    self.nombre,
            })

        except Exception as e:
            tiempo = round(time.time() - inicio, 3)
            print(f"[{self.nombre}] ERROR redimensionando {ruta_original.name}: {e}")
            with self.proceso._lock:
                self.proceso.redimensionamiento.registrar_fallo(
                    worker=self.nombre,
                    error=str(e)
                )


def iniciar_workers_redimension(n_workers, cola_conv, proceso):
    cola_redim = queue.Queue()

    print(f"\nETAPA 2 - REDIMENSIONAMIENTO | Workers: {n_workers}")

    workers = []
    for i in range(1, n_workers + 1):
        w = WorkerRedimension(
            nombre     = f"Worker-R{i}",
            cola_redim = cola_redim,
            cola_conv  = cola_conv,
            proceso    = proceso
        )
        workers.append(w)
        w.start()
        print(f"  Worker-R{i} iniciado")

    return cola_redim, workers