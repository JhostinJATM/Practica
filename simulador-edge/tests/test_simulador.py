import unittest
import os
import tempfile
from generador import GeneradorEventos

temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
os.environ['SIMULADOR_DB'] = temp_db.name

from persistencia import guardar_registro, obtener_pendientes, marcar_enviado, incrementar_intentos, obtener_conexion


class GeneradorEventosTests(unittest.TestCase):
    def setUp(self):
        os.environ['DORSAL_MIN'] = '10'
        os.environ['DORSAL_MAX'] = '20'
        os.environ['CONFIANZA_MIN'] = '50'
        os.environ['CONFIANZA_MAX'] = '60'
        self.generador = GeneradorEventos()

    def test_generar_evento_rango_dorsal(self):
        evento = self.generador.generar_evento()
        self.assertGreaterEqual(evento['dorsal'], 10)
        self.assertLessEqual(evento['dorsal'], 20)

    def test_generar_evento_rango_confianza(self):
        evento = self.generador.generar_evento()
        self.assertGreaterEqual(evento['confianza_ocr'], 50)
        self.assertLessEqual(evento['confianza_ocr'], 60)

    def test_generar_evento_tiempo_incremental(self):
        e1 = self.generador.generar_evento()
        e2 = self.generador.generar_evento()
        self.assertGreater(e2['tiempo_ms'], e1['tiempo_ms'])

    def test_generar_manual(self):
        evento = self.generador.generar_manual(7, 50000, 99.0)
        self.assertEqual(evento['dorsal'], 7)
        self.assertEqual(evento['tiempo_ms'], 50000)
        self.assertEqual(evento['confianza_ocr'], 99.0)


class PersistenciaTests(unittest.TestCase):
    def setUp(self):
        self.conn = obtener_conexion()
        self.conn.execute('DELETE FROM registros_pendientes')
        self.conn.commit()

    def test_guardar_y_obtener_pendientes(self):
        guardar_registro(1, 100000, 95.0)
        guardar_registro(2, 200000, 88.0)
        pendientes = obtener_pendientes()
        self.assertEqual(len(pendientes), 2)

    def test_marcar_enviado(self):
        guardar_registro(3, 150000, 90.0)
        pendientes = obtener_pendientes()
        marcar_enviado(pendientes[0]['id'])
        self.assertEqual(len(obtener_pendientes()), 0)

    def test_incrementar_intentos(self):
        guardar_registro(4, 120000, 70.0)
        pendientes = obtener_pendientes()
        incrementar_intentos(pendientes[0]['id'])
        pendientes = obtener_pendientes()
        self.assertEqual(pendientes[0]['intentos'], 1)


if __name__ == '__main__':
    unittest.main()
