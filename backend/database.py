"""
database.py - Capa de Base de Datos SQLite
==========================================
Guarda los metadatos de cada imagen procesada por etapa.
SQLite no necesita instalación — es un archivo pmic.db en backend/
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "pmic.db"

# Lock para acceso thread-safe a la base de datos
_lock_db = threading.Lock()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """
    Crea todas las tablas si no existen.
    Se llama una vez cuando arranca el servidor.
    """
    with _lock_db:
        conn = get_connection()
        cursor = conn.cursor()

        # Tabla de procesos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procesos (
                proceso_id   TEXT PRIMARY KEY,
                fecha_inicio TEXT,
                fecha_fin    TEXT,
                estado       TEXT,
                total_urls   INTEGER
            )
        """)

        # Tabla metadatos descarga
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadatos_descarga (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                proceso_id      TEXT,
                nombre_archivo  TEXT,
                fecha_descarga  TEXT,
                tamanio_mb      REAL,
                tiempo_descarga REAL,
                worker          TEXT
            )
        """)

        # Tabla metadatos redimensionamiento
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadatos_redimension (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                proceso_id           TEXT,
                nombre_original      TEXT,
                nombre_redimensionado TEXT,
                tiempo_procesamiento REAL,
                worker               TEXT
            )
        """)

        # Tabla metadatos conversion
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadatos_conversion (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                proceso_id           TEXT,
                nombre_original      TEXT,
                nombre_convertido    TEXT,
                formato_original     TEXT,
                tiempo_procesamiento REAL,
                worker               TEXT
            )
        """)

        # Tabla metadatos marca de agua
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadatos_marca_agua (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                proceso_id           TEXT,
                nombre_original      TEXT,
                nombre_final         TEXT,
                tiempo_procesamiento REAL,
                worker               TEXT
            )
        """)

        conn.commit()
        conn.close()
    print("Base de datos SQLite inicializada: pmic.db")


# ─────────────────────────────────────────────
# FUNCIONES DE ESCRITURA — una por etapa
# ─────────────────────────────────────────────

def guardar_proceso(proceso_id, total_urls):
    with _lock_db:
        conn = get_connection()
        conn.execute("""
            INSERT OR REPLACE INTO procesos
            (proceso_id, fecha_inicio, estado, total_urls)
            VALUES (?, ?, ?, ?)
        """, (proceso_id, datetime.now().isoformat(), "EN_PROCESO", total_urls))
        conn.commit()
        conn.close()


def actualizar_estado_proceso(proceso_id, estado):
    with _lock_db:
        conn = get_connection()
        conn.execute("""
            UPDATE procesos SET estado = ?, fecha_fin = ?
            WHERE proceso_id = ?
        """, (estado, datetime.now().isoformat(), proceso_id))
        conn.commit()
        conn.close()


def guardar_metadato_descarga(proceso_id, nombre, tamanio_mb, tiempo, worker):
    with _lock_db:
        conn = get_connection()
        conn.execute("""
            INSERT INTO metadatos_descarga
            (proceso_id, nombre_archivo, fecha_descarga, tamanio_mb, tiempo_descarga, worker)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (proceso_id, nombre, datetime.now().isoformat(), tamanio_mb, tiempo, worker))
        conn.commit()
        conn.close()


def guardar_metadato_redimension(proceso_id, nombre_original, nombre_nuevo, tiempo, worker):
    with _lock_db:
        conn = get_connection()
        conn.execute("""
            INSERT INTO metadatos_redimension
            (proceso_id, nombre_original, nombre_redimensionado, tiempo_procesamiento, worker)
            VALUES (?, ?, ?, ?, ?)
        """, (proceso_id, nombre_original, nombre_nuevo, tiempo, worker))
        conn.commit()
        conn.close()


def guardar_metadato_conversion(proceso_id, nombre_original, nombre_nuevo, formato_original, tiempo, worker):
    with _lock_db:
        conn = get_connection()
        conn.execute("""
            INSERT INTO metadatos_conversion
            (proceso_id, nombre_original, nombre_convertido, formato_original, tiempo_procesamiento, worker)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (proceso_id, nombre_original, nombre_nuevo, formato_original, tiempo, worker))
        conn.commit()
        conn.close()


def guardar_metadato_marca_agua(proceso_id, nombre_original, nombre_final, tiempo, worker):
    with _lock_db:
        conn = get_connection()
        conn.execute("""
            INSERT INTO metadatos_marca_agua
            (proceso_id, nombre_original, nombre_final, tiempo_procesamiento, worker)
            VALUES (?, ?, ?, ?, ?)
        """, (proceso_id, nombre_original, nombre_final, tiempo, worker))
        conn.commit()
        conn.close()


# ─────────────────────────────────────────────
# FUNCIONES DE CONSULTA
# ─────────────────────────────────────────────

def consultar_metadatos_proceso(proceso_id):
    """
    Retorna todos los metadatos de un proceso agrupados por etapa.
    Usado por el endpoint GET /api/estado/{id}
    """
    with _lock_db:
        conn = get_connection()

        descarga = conn.execute("""
            SELECT * FROM metadatos_descarga WHERE proceso_id = ?
        """, (proceso_id,)).fetchall()

        redimension = conn.execute("""
            SELECT * FROM metadatos_redimension WHERE proceso_id = ?
        """, (proceso_id,)).fetchall()

        conversion = conn.execute("""
            SELECT * FROM metadatos_conversion WHERE proceso_id = ?
        """, (proceso_id,)).fetchall()

        marca_agua = conn.execute("""
            SELECT * FROM metadatos_marca_agua WHERE proceso_id = ?
        """, (proceso_id,)).fetchall()

        conn.close()

    return {
        "descarga":           [dict(r) for r in descarga],
        "redimension":        [dict(r) for r in redimension],
        "conversion":         [dict(r) for r in conversion],
        "marca_agua":         [dict(r) for r in marca_agua],
    }