"""
downloader.py - Workers de Descarga
Diagrama Nivel 2: ETAPA 1 - Cajas verdes (Worker D1, D2...DN)
CONSUMIDOR de Cola de URLs - PRODUCTOR de Cola Redimensionamiento
"""

import os
import time
import queue
import threading
import requests
from pathlib import Path
from models import RegistroProceso

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
            nombre_archivo = self._nombre_desde_url(url)
            ruta_destino   = STORAGE_DIR / nombre_archivo
            respuesta = requests.get(url, timeout=30, stream=True)
            respuesta.raise_for_status()
            with open(ruta_destino, "wb") as f:
                for chunk in respuesta.iter_content(chunk_size=8192):
                    f.write(chunk)
            tiempo_descarga = round(time.time() - inicio, 3)
            tamanio_mb      = round(os.path.getsize(ruta_destino) / (1024 * 1024), 4)
            with self.proceso._lock:
                self.proceso.descarga.registrar_exito(tiempo=tiempo_descarga, worker=self.nombre)
            print(f"[{self.nombre}] OK: {nombre_archivo} ({tamanio_mb} MB en {tiempo_descarga}s)")
            self.cola_redim.put({
                "ruta":            str(ruta_destino),
                "nombre_original": nombre_archivo,
                "url_origen":      url,
                "tamanio_mb":      tamanio_mb,
                "worker_descarga": self.nombre,
            })
        except Exception as e:
            print(f"[{self.nombre}] ERROR: {url} -> {e}")
            with self.proceso._lock:
                self.proceso.descarga.registrar_fallo(worker=self.nombre, error=str(e))

    def _nombre_desde_url(self, url):
        from urllib.parse import urlparse
        import uuid
        path   = urlparse(url).path
        nombre = Path(path).name
        if not nombre or "." not in nombre:
            nombre = f"imagen_{uuid.uuid4().hex[:8]}.jpg"
        return nombre


def iniciar_workers_descarga(urls, n_workers, cola_redim, proceso):
    cola_urls = queue.Queue()
    for url in urls:
        cola_urls.put(url)
    print(f"\nETAPA 1 - DESCARGA | URLs: {len(urls)} | Workers: {n_workers}")
    workers = []
    for i in range(1, n_workers + 1):
        worker = WorkerDescarga(
            nombre=f"Worker-D{i}",
            cola_urls=cola_urls,
            cola_redim=cola_redim,
            proceso=proceso
        )
        workers.append(worker)
        worker.start()
        print(f"  Worker-D{i} iniciado")
    return cola_urls, workers