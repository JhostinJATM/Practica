import requests
import os
import time
import threading


class ClienteHTTP:
    def __init__(self, log_callback=None):
        self.backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
        self.token = os.environ.get('EDGE_TOKEN', '')
        self.log = log_callback or print
        self._sesion = requests.Session()
        self._sesion.headers.update({'Authorization': f'Token {self.token}'})

    def verificar_conexion(self):
        try:
            url = f'{self.backend_url}/api/health/'
            resp = self._sesion.get(url, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def obtener_competencia(self):
        try:
            url = f'{self.backend_url}/api/competencias/?is_active=true&is_running=true'
            resp = self._sesion.get(url, timeout=5)
            if resp.status_code == 200 and resp.json():
                return resp.json()[0].get('name', 'Desconocida')
        except Exception:
            pass
        return 'Desconocida'

    def enviar_registro(self, dorsal, tiempo_ms, confianza_ocr, intentos_max=3):
        url = f'{self.backend_url}/api/registros/'
        payload = {
            'dorsal': dorsal,
            'tiempo_ms': tiempo_ms,
            'confianza_ocr': confianza_ocr,
        }

        for intento in range(intentos_max):
            try:
                resp = self._sesion.post(url, json=payload, timeout=10)
                if resp.status_code == 201:
                    data = resp.json()
                    return True, data
                else:
                    error = resp.json().get('error', resp.text)
                    self.log(f'Error {resp.status_code}: {error}')
                    if intento < intentos_max - 1:
                        time.sleep(10)
            except Exception as e:
                self.log(f'Error de conexion (intento {intento + 1}/{intentos_max}): {e}')
                if intento < intentos_max - 1:
                    time.sleep(10)

        return False, None

    def procesar_pendientes(self, obtener_pendientes, marcar_enviado, incrementar_intentos):
        from persistencia import obtener_pendientes as op, marcar_enviado as me, incrementar_intentos as ii
        pendientes = op()
        for p in pendientes:
            exito, data = self.enviar_registro(p['dorsal'], p['tiempo_ms'], p['confianza_ocr'])
            if exito:
                estado = data.get('estado', '?')
                record_id = data.get('record_id')
                # Si quedo pendiente, actualizar record_id en la BD local
                if estado == 'pendiente' and record_id and not p.get('record_id'):
                    from persistencia import obtener_conexion
                    conn = obtener_conexion()
                    conn.execute('UPDATE registros_pendientes SET record_id = ? WHERE id = ?', (record_id, p['id']))
                    conn.commit()
                    conn.close()
                else:
                    me(p['id'])
                    self.log(f'[Reenviado] Dorsal {p["dorsal"]} - {p["tiempo_ms"]}ms - {data.get("estado", "?")}')
            else:
                ii(p['id'])

    def verificar_estado_registro(self, record_id):
        """Consulta el estado actual de un registro en el servidor."""
        url = f'{self.backend_url}/api/registros/{record_id}/estado/'
        try:
            resp = self._sesion.get(url, timeout=10)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get('error', f'Error {resp.status_code}')
        except Exception as e:
            return False, str(e)
