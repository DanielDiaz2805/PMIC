"""
watermark.py - Workers de Marca de Agua
    print("ETAPA 4 - MARCA DE AGUA | Workers:", n_workers)
CONSUMIDOR de Cola Marca de Agua - escribe resultado final en disco
"""

import time
import queue
import threading
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from models import RegistroProceso

TEXTO_MARCA = "PMIC"


class WorkerMarcaAgua(threading.Thread):
    def __init__(self, nombre, cola_marca, proceso):
        super().__init__(name=nombre, daemon=True)
        self.nombre     = nombre
        self.cola_marca = cola_marca
        self.proceso    = proceso

    def run(self):
        while True:
            try:
                item = self.cola_marca.get(timeout=5)
            except queue.Empty:
                break
            self._aplicar_marca(item)
            self.cola_marca.task_done()

    def _aplicar_marca(self, item):
        inicio        = time.time()
        ruta_original = Path(item["ruta"])
        try:
            with Image.open(ruta_original) as img:
                img_marca = img.copy()
                draw      = ImageDraw.Draw(img_marca)
                ancho, alto = img_marca.size
                try:
                    tamanio_fuente = max(20, ancho // 15)
                    fuente = ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        tamanio_fuente
                    )
                except (IOError, OSError):
                    fuente = ImageFont.load_default()
                bbox        = draw.textbbox((0, 0), TEXTO_MARCA, font=fuente)
                ancho_texto = bbox[2] - bbox[0]
                alto_texto  = bbox[3] - bbox[1]
                margen = 20
                x = ancho - ancho_texto - margen
                y = alto  - alto_texto  - margen
                draw.text((x + 2, y + 2), TEXTO_MARCA, font=fuente, fill=(0, 0, 0, 128))
                draw.text((x, y), TEXTO_MARCA, font=fuente, fill=(255, 255, 255, 200))
                nombre_nuevo = ruta_original.stem + "_marca_agua.png"
                ruta_nueva   = ruta_original.parent / nombre_nuevo
                img_marca.save(ruta_nueva, format="PNG")
            tiempo_proc = round(time.time() - inicio, 3)
            with self.proceso._lock:
                self.proceso.marca_agua.registrar_exito(tiempo=tiempo_proc, worker=self.nombre)
            print(f"[{self.nombre}] OK: {nombre_nuevo} en {tiempo_proc}s")
        except Exception as e:
            print(f"[{self.nombre}] ERROR en {ruta_original.name}: {e}")
            with self.proceso._lock:
                self.proceso.marca_agua.registrar_fallo(worker=self.nombre, error=str(e))


def iniciar_workers_marca_agua(n_workers, proceso):
    cola_marca = queue.Queue()
    print("ETAPA 4 - MARCA DE AGUA | Workers:", n_workers)
    workers = []
    for i in range(1, n_workers + 1):
        worker = WorkerMarcaAgua(
            nombre     = f"Worker-M{i}",
            cola_marca = cola_marca,
            proceso    = proceso
        )
        workers.append(worker)
        worker.start()
        print(f"  Worker-M{i} iniciado")
    return cola_marca, workers