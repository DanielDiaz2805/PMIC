

import threading
from models import RegistroProceso, obtener_proceso, EstadoProceso
from downloader import iniciar_workers_descarga
from resizer import iniciar_workers_redimension
from converter import iniciar_workers_conversion
from watermark import iniciar_workers_marca_agua


def ejecutar_pipeline(proceso_id: str, urls: list, config_workers: dict):
    """
    Funcion principal del pipeline.
    Llamada en un hilo separado para no bloquear la API.

    config_workers = {
        "descarga":           N,
        "redimensionamiento": N,
        "conversion":         N,
        "marca_agua":         N
    }
    """

    proceso = obtener_proceso(proceso_id)
    if not proceso:
        print(f"ERROR: proceso {proceso_id} no encontrado")
        return

    print(f"\n{'='*55}")
    print(f"INICIANDO PIPELINE PMIC")
    print(f"Proceso ID:     {proceso_id[:8]}...")
    print(f"Total imagenes: {len(urls)}")
    print(f"{'='*55}")

    try:
        # ─────────────────────────────────────────────────
        # Crear colas de atras hacia adelante
        # Cada etapa ya tiene su cola destino lista
        # cuando arranca
        # ─────────────────────────────────────────────────

        # Etapa 4 - Cola de Marca de Agua (ultima etapa)
        cola_marca, workers_marca = iniciar_workers_marca_agua(
            n_workers = config_workers.get("marca_agua", 2),
            proceso   = proceso
        )

        # Etapa 3 - Cola de Conversion
        cola_conv, workers_conv = iniciar_workers_conversion(
            n_workers  = config_workers.get("conversion", 2),
            cola_marca = cola_marca,
            proceso    = proceso
        )

        # Etapa 2 - Cola de Redimensionamiento
        cola_redim, workers_redim = iniciar_workers_redimension(
            n_workers = config_workers.get("redimensionamiento", 2),
            cola_conv = cola_conv,
            proceso   = proceso
        )

        # Etapa 1 - Cola de URLs + Workers Descarga (primera etapa)
        cola_urls, workers_desc = iniciar_workers_descarga(
            urls       = urls,
            n_workers  = config_workers.get("descarga", 2),
            cola_redim = cola_redim,
            proceso    = proceso
        )

        # ─────────────────────────────────────────────────
        # Esperar que cada etapa termine en orden
        # ─────────────────────────────────────────────────

        for w in workers_desc:
            w.join()
        print("\nEtapa 1 completada - Descarga finalizada")

        for w in workers_redim:
            w.join()
        print("Etapa 2 completada - Redimensionamiento finalizado")

        for w in workers_conv:
            w.join()
        print("Etapa 3 completada - Conversion finalizada")

        for w in workers_marca:
            w.join()
        print("Etapa 4 completada - Marca de agua finalizada")

        # ─────────────────────────────────────────────────
        # Actualizar estado final del proceso
        # ─────────────────────────────────────────────────
        proceso.actualizar_estado()

        print(f"\n{'='*55}")
        print(f"PIPELINE COMPLETADO")
        print(f"Estado final:  {proceso.estado.value}")
        print(f"Procesadas:    {proceso.marca_agua.total_procesados}/{len(urls)}")
        print(f"Fallidas:      {proceso.total_fallidos}")
        print(f"Tiempo total:  {proceso.tiempo_total_ejecucion:.2f}s")
        print(f"{'='*55}\n")

    except Exception as e:
        print(f"ERROR CRITICO en pipeline: {e}")
        with proceso._lock:
            proceso.estado = EstadoProceso.FALLIDO


def iniciar_pipeline_async(proceso_id: str, urls: list, config_workers: dict):
    """
    Arranca el pipeline en un hilo separado.
    La API llama esta funcion y retorna inmediatamente
    el proceso_id al usuario SIN esperar que el pipeline termine.
    Eso es lo que hace el sistema no-bloqueante.
    """
    hilo = threading.Thread(
        target = ejecutar_pipeline,
        args   = (proceso_id, urls, config_workers),
        daemon = True,
        name   = f"Pipeline-{proceso_id[:8]}"
    )
    hilo.start()
    return hilo