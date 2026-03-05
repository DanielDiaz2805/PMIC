"""
downloader.py - Workers de Descarga
Diagrama Nivel 2: ETAPA 1 - Cajas verdes (Worker D1, D2...DN)
CONSUMIDOR de Cola URLs - PRODUCTOR de Cola Redimensionamiento
"""

import time
import queue
import threading
import requests
from pathlib import Path
from datetime import datetime
from models import RegistroProceso
from database import guardar_metadato_descarga

STORAGE_DIR = Path(__file__).parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True)


class WorkerDescarga(threading.Thread):
    def __init__(self, nombre, cola_urls, cola_redim, proceso):
        super().__init__(name=nombre, daemon=True)
        self.nombre     = nombre
        self.cola_urls  = cola_urls
        self.cola_redim = cola_redim
        self.proceso    = proceso

    def run(self):
        while True:
            try:
                url = self.cola_urls.get(timeout=2)
            except queue.Empty:
                break
            self._descargar(url)
            self.cola_urls.task_done()

    def _descargar(self, url):
        inicio = time.time()
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            nombre = self._nombre_desde_url(url)
            ruta   = STORAGE_DIR / nombre

            with open(ruta, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            tiempo     = round(time.time() - inicio, 3)
            tamanio_mb = round(ruta.stat().st_size / (1024 * 1024), 4)

            # Guardar en memoria (métricas)
            with self.proceso._lock:
                self.proceso.descarga.registrar_exito(
                    tiempo=tiempo,
                    worker=self.nombre
                )

            # Guardar en base de datos SQLite
            guardar_metadato_descarga(
                proceso_id = self.proceso.proceso_id,
                nombre     = nombre,
                tamanio_mb = tamanio_mb,
                tiempo     = tiempo,
                worker     = self.nombre
            )

            print(f"[{self.nombre}] OK: {nombre} ({tamanio_mb} MB en {tiempo}s)")

            self.cola_redim.put({
                "ruta":            str(ruta),
                "nombre_original": nombre,
                "url_origen":      url,
                "tamanio_mb":      tamanio_mb,
                "worker_descarga": self.nombre,
            })

        except Exception as e:
            tiempo = round(time.time() - inicio, 3)
            print(f"[{self.nombre}] ERROR descargando {url}: {e}")
            with self.proceso._lock:
                self.proceso.descarga.registrar_fallo(
                    worker=self.nombre,
                    error=str(e)
                )

    def _nombre_desde_url(self, url):
        import uuid
        nombre = url.split("/")[-1].split("?")[0]
        if not nombre or "." not in nombre:
            nombre = f"{uuid.uuid4().hex[:8]}.jpg"
        return nombre


def iniciar_workers_descarga(urls, n_workers, cola_redim, proceso):
    cola_urls = queue.Queue()
    for url in urls:
        cola_urls.put(url)

    print(f"\nETAPA 1 - DESCARGA | URLs: {len(urls)} | Workers: {n_workers}")

    workers = []
    for i in range(1, n_workers + 1):
        w = WorkerDescarga(
            nombre     = f"Worker-D{i}",
            cola_urls  = cola_urls,
            cola_redim = cola_redim,
            proceso    = proceso
        )
        workers.append(w)
        w.start()
        print(f"  Worker-D{i} iniciado")

    return cola_urls, workers