import random
import time
import os


class GeneradorEventos:
    def __init__(self):
        self.dorsal_min = int(os.environ.get('DORSAL_MIN', 1))
        self.dorsal_max = int(os.environ.get('DORSAL_MAX', 50))
        self.confianza_min = float(os.environ.get('CONFIANZA_MIN', 0))
        self.confianza_max = float(os.environ.get('CONFIANZA_MAX', 100))
        self.tiempo_base = 0
        self.tiempo_incremento = int(os.environ.get('TIEMPO_INCREMENTO_MS', 5000))

    def generar_evento(self):
        dorsal = random.randint(self.dorsal_min, self.dorsal_max)
        self.tiempo_base += random.randint(3000, self.tiempo_incremento)
        confianza = round(random.uniform(self.confianza_min, self.confianza_max), 2)
        return {
            'dorsal': dorsal,
            'tiempo_ms': self.tiempo_base,
            'confianza_ocr': confianza,
        }

    def generar_manual(self, dorsal, tiempo_ms, confianza_ocr):
        return {
            'dorsal': dorsal,
            'tiempo_ms': tiempo_ms,
            'confianza_ocr': confianza_ocr,
        }
