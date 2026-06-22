import sqlite3
import os
import json
from datetime import datetime


DB_PATH = os.environ.get('SIMULADOR_DB', 'simulador.db')


def obtener_conexion():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS registros_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dorsal INTEGER NOT NULL,
            tiempo_ms INTEGER NOT NULL,
            confianza_ocr REAL NOT NULL,
            record_id TEXT,
            enviado INTEGER DEFAULT 0,
            intentos INTEGER DEFAULT 0,
            creado_en TEXT NOT NULL,
            ultimo_intento TEXT
        )
    ''')
    # Agregar columna record_id si no existe (migracion ligera)
    try:
        conn.execute('ALTER TABLE registros_pendientes ADD COLUMN record_id TEXT')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


def guardar_registro(dorsal, tiempo_ms, confianza_ocr, record_id=None):
    conn = obtener_conexion()
    conn.execute(
        'INSERT INTO registros_pendientes (dorsal, tiempo_ms, confianza_ocr, record_id, creado_en) VALUES (?, ?, ?, ?, ?)',
        (dorsal, tiempo_ms, confianza_ocr, record_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def marcar_enviado(registro_id):
    conn = obtener_conexion()
    conn.execute('UPDATE registros_pendientes SET enviado = 1 WHERE id = ?', (registro_id,))
    conn.commit()
    conn.close()


def incrementar_intentos(registro_id):
    conn = obtener_conexion()
    conn.execute(
        'UPDATE registros_pendientes SET intentos = intentos + 1, ultimo_intento = ? WHERE id = ?',
        (datetime.now().isoformat(), registro_id)
    )
    conn.commit()
    conn.close()


def obtener_pendientes():
    conn = obtener_conexion()
    rows = conn.execute(
        'SELECT id, dorsal, tiempo_ms, confianza_ocr, record_id, intentos FROM registros_pendientes WHERE enviado = 0 ORDER BY id'
    ).fetchall()
    conn.close()
    return [{'id': r[0], 'dorsal': r[1], 'tiempo_ms': r[2], 'confianza_ocr': r[3], 'record_id': r[4], 'intentos': r[5]} for r in rows]


def obtener_pendientes_con_record_id():
    """Obtiene solo registros que ya tienen record_id asignado (para verificacion de estado)."""
    conn = obtener_conexion()
    rows = conn.execute(
        'SELECT id, record_id FROM registros_pendientes WHERE enviado = 0 AND record_id IS NOT NULL ORDER BY id'
    ).fetchall()
    conn.close()
    return [{'id': r[0], 'record_id': r[1]} for r in rows]


def limpiar_enviados():
    conn = obtener_conexion()
    conn.execute('DELETE FROM registros_pendientes WHERE enviado = 1')
    conn.commit()
    conn.close()
