"""
converter.py - Workers de Conversion de Formato
Diagrama Nivel 2: ETAPA 3 - Cajas naranjas (Worker C1, C2...CN)
CONSUMIDOR de Cola Conversion - PRODUCTOR de Cola Marca de Agua
"""

import time
import queue
import threading
from pathlib import Path
from PIL import Image
from models import RegistroProceso

FORMATO_DESTINO = "PNG"


class WorkerConversion(threading.Thread):
    """
    Cada instancia es un hilo independiente.
    Diagrama Nivel 2: caja naranja Worker C1, C2...CN

    Ciclo de vida:
    1. Saca imagen de cola_conv         (CONSUMIDOR)
    2. Convierte formato a PNG
    3. Guarda con sufijo _formato_cambiado
    4. Mete ruta en cola_marca          (PRODUCTOR)
    5. Repite hasta que no haya mas trabajo
    """

    def __init__(self, nombre, cola_conv, cola_marca, proceso):
        super().__init__(name=nombre, daemon=True)
        self.nombre     = nombre
        self.cola_conv  = cola_conv
        self.cola_marca = cola_marca
        self.proceso    = proceso

    def run(self):
        while True:
            try:
                item = self.cola_conv.get(timeout=5)
            except queue.Empty:
                break
            self._convertir(item)
            self.cola_conv.task_done()

    def _convertir(self, item):
        inicio        = time.time()
        ruta_original = Path(item["ruta"])

        try:
            with Image.open(ruta_original) as img:
                formato_original = img.format or ruta_original.suffix[1:].upper()

                # Convertir modo segun sea necesario
                if img.mode in ("RGBA", "P"):
                    img_conv = img.convert("RGBA")
                else:
                    img_conv = img.convert("RGB")

                # Guardar con sufijo _formato_cambiado y extension .png
                nombre_nuevo = ruta_original.stem + "_formato_cambiado.png"
                ruta_nueva   = ruta_original.parent / nombre_nuevo
                img_conv.save(ruta_nueva, format=FORMATO_DESTINO)

            tiempo_proc = round(time.time() - inicio, 3)

            # Registrar en modulo de metricas
            with self.proceso._lock:
                self.proceso.conversion.registrar_exito(
                    tiempo=tiempo_proc,
                    worker=self.nombre
                )

            print(f"[{self.nombre}] OK: {formato_original} -> PNG | "
                  f"{nombre_nuevo} en {tiempo_proc}s")

            # Pasar a la siguiente etapa - Cola de Marca de Agua
            self.cola_marca.put({
                **item,
                "ruta":              str(ruta_nueva),
                "nombre_convertido": nombre_nuevo,
                "formato_original":  formato_original,
                "formato_final":     FORMATO_DESTINO,
                "worker_conversion": self.nombre,
            })

        except Exception as e:
            tiempo_proc = round(time.time() - inicio, 3)
            print(f"[{self.nombre}] ERROR convirtiendo {ruta_original.name}: {e}")
            with self.proceso._lock:
                self.proceso.conversion.registrar_fallo(
                    worker=self.nombre,
                    error=str(e)
                )


def iniciar_workers_conversion(n_workers, cola_marca, proceso):
    """
    Funcion usada por pipeline.py para arrancar la Etapa 3.
    Crea la Cola de Conversion y lanza N workers.
    Retorna la cola para que los workers de redimension produzcan en ella.
    """
    cola_conv = queue.Queue()

    print(f"\nETAPA 3 - CONVERSION DE FORMATO | Workers: {n_workers}")

    workers = []
    for i in range(1, n_workers + 1):
        worker = WorkerConversion(
            nombre     = f"Worker-C{i}",
            cola_conv  = cola_conv,
            cola_marca = cola_marca,
            proceso    = proceso
        )
        workers.append(worker)
        worker.start()
        print(f"  Worker-C{i} iniciado")

    return cola_conv, workers