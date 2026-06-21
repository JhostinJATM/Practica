from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from app.models import Competencia, Juez, Equipo, RegistroTiempo, AuditoriaRegistro
from django.utils import timezone
import uuid
import json


class RegistroTiempoModelTests(TestCase):
    def setUp(self):
        self.juez = Juez.objects.create(username='juez_test', first_name='Test', last_name='Juez')
        self.juez.set_password('password123')
        self.juez.save()
        self.competencia = Competencia.objects.create(name='Carrera 5K', datetime='2025-06-01T08:00:00Z')
        self.equipo = Equipo.objects.create(name='Los Veloces', number=42, category='estudiantes', competition=self.competencia, judge=self.juez)

    def test_crear_registro_automatico(self):
        registro = RegistroTiempo.objects.create(
            team=self.equipo, time=125000, hours=0, minutes=2, seconds=5, milliseconds=0,
            origen='automatico', confianza_ocr=98.5, estado='validado', dorsal_detectado=42
        )
        self.assertEqual(registro.origen, 'automatico')
        self.assertEqual(registro.estado, 'validado')
        self.assertEqual(registro.confianza_ocr, 98.5)
        self.assertEqual(registro.dorsal_detectado, 42)
        self.assertIsNone(registro.dorsal_corregido)
        self.assertIsNone(registro.validado_por)
        self.assertEqual(registro.team, self.equipo)

    def test_crear_registro_pendiente(self):
        registro = RegistroTiempo.objects.create(
            team=self.equipo, time=89000, hours=0, minutes=1, seconds=29, milliseconds=0,
            origen='manual', confianza_ocr=50.0, estado='pendiente', dorsal_detectado=42
        )
        self.assertEqual(registro.estado, 'pendiente')
        self.assertEqual(registro.origen, 'manual')

    def test_registro_descalificado_con_motivo(self):
        registro = RegistroTiempo.objects.create(
            team=self.equipo, time=100000, hours=0, minutes=1, seconds=40, milliseconds=0,
            origen='manual', confianza_ocr=40.0, estado='descalificado', dorsal_detectado=42,
            motivo_descalificacion='Fuera de carril'
        )
        self.assertEqual(registro.estado, 'descalificado')
        self.assertEqual(registro.motivo_descalificacion, 'Fuera de carril')

    def test_dorsal_corregido_preserva_original(self):
        registro = RegistroTiempo.objects.create(
            team=self.equipo, time=50000, hours=0, minutes=0, seconds=50, milliseconds=0,
            origen='manual', confianza_ocr=60.0, estado='corregido', dorsal_detectado=42,
            dorsal_corregido=24
        )
        self.assertEqual(registro.dorsal_detectado, 42)
        self.assertEqual(registro.dorsal_corregido, 24)

    def test_evidencia_imagen_null(self):
        registro = RegistroTiempo.objects.create(
            team=self.equipo, time=75000, hours=0, minutes=1, seconds=15, milliseconds=0,
            origen='automatico', confianza_ocr=99.0, estado='validado', dorsal_detectado=7
        )
        self.assertFalse(registro.evidencia_imagen)

    def test_validado_por_juez(self):
        registro = RegistroTiempo.objects.create(
            team=self.equipo, time=60000, hours=0, minutes=1, seconds=0, milliseconds=0,
            origen='manual', confianza_ocr=80.0, estado='validado', dorsal_detectado=42,
            validado_por=self.juez, validado_en=timezone.now()
        )
        self.assertEqual(registro.validado_por, self.juez)
        self.assertIsNotNone(registro.validado_en)


class AuditoriaRegistroModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='juez', password='test123')
        self.juez = Juez.objects.create(user=self.user, username='juez', first_name='J', last_name='P')
        self.competencia = Competencia.objects.create(name='Carrera', datetime='2025-06-01T08:00:00Z')
        self.equipo = Equipo.objects.create(name='Equipo A', number=1, category='estudiantes', competition=self.competencia)
        self.registro = RegistroTiempo.objects.create(
            team=self.equipo, time=100000, hours=0, minutes=1, seconds=40, milliseconds=0,
            origen='manual', confianza_ocr=50.0, estado='pendiente', dorsal_detectado=1
        )

    def test_crear_auditoria_confirmar(self):
        auditoria = AuditoriaRegistro.objects.create(
            registro_tiempo=self.registro, juez=self.juez, accion='confirmar',
            valor_anterior={'estado': 'pendiente'}, valor_nuevo={'estado': 'validado'}
        )
        self.assertEqual(auditoria.accion, 'confirmar')
        self.assertEqual(auditoria.registro_tiempo, self.registro)
        self.assertEqual(auditoria.juez, self.juez)
        self.assertIsNotNone(auditoria.creado_en)

    def test_auditoria_corregir_con_dorsal(self):
        auditoria = AuditoriaRegistro.objects.create(
            registro_tiempo=self.registro, juez=self.juez, accion='corregir',
            valor_anterior={'estado': 'pendiente', 'dorsal_detectado': 1},
            valor_nuevo={'estado': 'corregido', 'dorsal_corregido': 5}
        )
        self.assertEqual(auditoria.valor_anterior['dorsal_detectado'], 1)
        self.assertEqual(auditoria.valor_nuevo['dorsal_corregido'], 5)

    def test_auditoria_descalificar(self):
        auditoria = AuditoriaRegistro.objects.create(
            registro_tiempo=self.registro, juez=self.juez, accion='descalificar',
            valor_anterior={'estado': 'pendiente'},
            valor_nuevo={'estado': 'descalificado', 'motivo_descalificacion': 'Fuera de carril'}
        )
        self.assertEqual(auditoria.valor_nuevo['motivo_descalificacion'], 'Fuera de carril')


class EdgeTokenAuthTests(TestCase):
    def setUp(self):
        self.competencia = Competencia.objects.create(name='Carrera Activa', datetime='2025-06-01T08:00:00Z')
        self.client = APIClient()

    def test_token_valido(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 1, 'tiempo_ms': 100000, 'confianza_ocr': 99.0},
            HTTP_AUTHORIZATION=f'Token {self.competencia.token}'
        )
        self.assertIn(response.status_code, [201, 400])  # 400 si no existe equipo

    def test_token_invalido(self):
        fake_token = uuid.uuid4()
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 1, 'tiempo_ms': 100000, 'confianza_ocr': 99.0},
            HTTP_AUTHORIZATION=f'Token {fake_token}'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sin_token(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 1, 'tiempo_ms': 100000, 'confianza_ocr': 99.0}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EdgeRegistroAPITests(TestCase):
    def setUp(self):
        self.competencia = Competencia.objects.create(name='Carrera 5K', datetime='2025-06-01T08:00:00Z')
        self.competencia.is_running = True
        self.competencia.save()
        self.juez = Juez.objects.create(username='juez_auto', first_name='Auto', last_name='Juez')
        self.juez.set_password('password')
        self.juez.save()
        self.equipo = Equipo.objects.create(name='Los Veloces', number=42, category='estudiantes', competition=self.competencia, judge=self.juez)
        self.client = APIClient()
        self.auth_header = f'Token {self.competencia.token}'

    def test_auto_validacion_ocr_alta(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 42, 'tiempo_ms': 125000, 'confianza_ocr': 98.5},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['estado'], 'validado')
        self.assertEqual(data['equipo_id'], self.equipo.id)
        self.assertEqual(data['dorsal_detectado'], 42)

    def test_registro_pendiente_ocr_baja(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 42, 'tiempo_ms': 89000, 'confianza_ocr': 50.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['estado'], 'pendiente')

    def test_dorsal_no_encontrado(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 999, 'tiempo_ms': 100000, 'confianza_ocr': 99.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Dorsal no encontrado', response.json()['error'])

    def test_confianza_limite_95(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 42, 'tiempo_ms': 100000, 'confianza_ocr': 95.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['estado'], 'validado')

    def test_confianza_limite_94_9(self):
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 42, 'tiempo_ms': 100000, 'confianza_ocr': 94.9},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['estado'], 'pendiente')

    def test_competencia_no_activa(self):
        self.competencia.is_active = False
        self.competencia.save()
        response = self.client.post(
            '/api/registros/',
            {'dorsal': 42, 'tiempo_ms': 100000, 'confianza_ocr': 99.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ValidacionPanelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='juez_val', password='test1234')
        self.juez = Juez.objects.create(user=self.user, username='juez_val', first_name='Val', last_name='Juez')
        self.juez.set_password('test1234')
        self.juez.save()
        self.competencia = Competencia.objects.create(name='Carrera Val', datetime='2025-06-01T08:00:00Z')
        self.competencia.is_running = True
        self.competencia.save()
        self.equipo = Equipo.objects.create(name='Equipo X', number=10, category='estudiantes', competition=self.competencia, judge=self.juez)
        self.registro = RegistroTiempo.objects.create(
            team=self.equipo, time=50000, hours=0, minutes=0, seconds=50, milliseconds=0,
            origen='manual', confianza_ocr=50.0, estado='pendiente', dorsal_detectado=10
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_confirmar_registro_pendiente(self):
        url = f'/api/validacion/{self.registro.record_id}/confirmar/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.registro.refresh_from_db()
        self.assertEqual(self.registro.estado, 'validado')
        self.assertEqual(self.registro.validado_por, self.juez)

    def test_confirmar_registro_ya_validado(self):
        self.registro.estado = 'validado'
        self.registro.save()
        url = f'/api/validacion/{self.registro.record_id}/confirmar/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_corregir_dorsal_valido(self):
        otro_equipo = Equipo.objects.create(name='Equipo Y', number=20, category='estudiantes', competition=self.competencia)
        url = f'/api/validacion/{self.registro.record_id}/corregir/'
        response = self.client.post(url, {'dorsal_corregido': 20}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.registro.refresh_from_db()
        self.assertEqual(self.registro.estado, 'corregido')
        self.assertEqual(self.registro.dorsal_corregido, 20)
        self.assertEqual(self.registro.dorsal_detectado, 10)

    def test_corregir_dorsal_inexistente(self):
        url = f'/api/validacion/{self.registro.record_id}/corregir/'
        response = self.client.post(url, {'dorsal_corregido': 999}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no pertenece', response.json()['error'])

    def test_descalificar_con_motivo(self):
        url = f'/api/validacion/{self.registro.record_id}/descalificar/'
        response = self.client.post(url, {'motivo': 'Fuera de carril'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.registro.refresh_from_db()
        self.assertEqual(self.registro.estado, 'descalificado')
        self.assertEqual(self.registro.motivo_descalificacion, 'Fuera de carril')

    def test_descalificar_sin_motivo(self):
        url = f'/api/validacion/{self.registro.record_id}/descalificar/'
        response = self.client.post(url, {'motivo': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_listar_pendientes(self):
        response = self.client.get('/api/validacion/pendientes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()['pendientes']), 1)

    def test_auditoria_registrada_tras_confirmar(self):
        url = f'/api/validacion/{self.registro.record_id}/confirmar/'
        self.client.post(url)
        auditoria = AuditoriaRegistro.objects.filter(registro_tiempo=self.registro, accion='confirmar').first()
        self.assertIsNotNone(auditoria)
        self.assertEqual(auditoria.juez, self.juez)
        self.assertEqual(auditoria.valor_anterior['estado'], 'pendiente')
        self.assertEqual(auditoria.valor_nuevo['estado'], 'validado')

    def test_auditoria_registrada_tras_descalificar(self):
        url = f'/api/validacion/{self.registro.record_id}/descalificar/'
        self.client.post(url, {'motivo': 'Fuera de carril'}, format='json')
        auditoria = AuditoriaRegistro.objects.filter(registro_tiempo=self.registro, accion='descalificar').first()
        self.assertIsNotNone(auditoria)
        self.assertEqual(auditoria.valor_nuevo['motivo_descalificacion'], 'Fuera de carril')


class IntegracionFlujoCompletoTests(TestCase):
    """Prueba del flujo completo: Edge -> registro -> validacion -> clasificacion."""

    def setUp(self):
        self.user = User.objects.create_user(username='juez_int', password='test1234')
        self.juez = Juez.objects.create(user=self.user, username='juez_int', first_name='Int', last_name='Juez')
        self.juez.set_password('test1234')
        self.juez.save()
        self.competencia = Competencia.objects.create(name='Carrera Integracion', datetime='2025-06-01T08:00:00Z')
        self.competencia.is_running = True
        self.competencia.save()
        self.equipo_a = Equipo.objects.create(name='Equipo A', number=1, category='estudiantes', competition=self.competencia)
        self.equipo_b = Equipo.objects.create(name='Equipo B', number=2, category='estudiantes', competition=self.competencia)
        self.edge_client = APIClient()
        self.auth_header = f'Token {self.competencia.token}'

    def test_flujo_completo_auto_validacion(self):
        response = self.edge_client.post(
            '/api/registros/',
            {'dorsal': 1, 'tiempo_ms': 120000, 'confianza_ocr': 99.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['estado'], 'validado')
        self.assertEqual(response.json()['equipo_id'], self.equipo_a.id)

        registro = RegistroTiempo.objects.get(record_id=response.json()['record_id'])
        self.assertEqual(registro.origen, 'automatico')
        self.assertEqual(registro.estado, 'validado')

    def test_flujo_completo_pendiente_validacion(self):
        resp_edge = self.edge_client.post(
            '/api/registros/',
            {'dorsal': 2, 'tiempo_ms': 95000, 'confianza_ocr': 50.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.assertEqual(resp_edge.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_edge.json()['estado'], 'pendiente')
        record_id = resp_edge.json()['record_id']

        registro = RegistroTiempo.objects.get(record_id=record_id)
        self.assertEqual(registro.origen, 'manual')

        val_client = APIClient()
        val_client.force_authenticate(user=self.user)

        pendientes = val_client.get('/api/validacion/pendientes/').json()
        self.assertGreaterEqual(len(pendientes['pendientes']), 1)

        resp_confirm = val_client.post(f'/api/validacion/{record_id}/confirmar/')
        self.assertEqual(resp_confirm.status_code, status.HTTP_200_OK)
        registro.refresh_from_db()
        self.assertEqual(registro.estado, 'validado')

        auditoria = AuditoriaRegistro.objects.filter(
            registro_tiempo=registro, accion='confirmar'
        ).first()
        self.assertIsNotNone(auditoria)

    def test_flujo_descalificacion(self):
        resp_edge = self.edge_client.post(
            '/api/registros/',
            {'dorsal': 1, 'tiempo_ms': 80000, 'confianza_ocr': 30.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        record_id = resp_edge.json()['record_id']

        val_client = APIClient()
        val_client.force_authenticate(user=self.user)
        val_client.post(
            f'/api/validacion/{record_id}/descalificar/',
            {'motivo': 'Fuera de carril'}, format='json'
        )

        registro = RegistroTiempo.objects.get(record_id=record_id)
        self.assertEqual(registro.estado, 'descalificado')
        self.assertEqual(registro.motivo_descalificacion, 'Fuera de carril')

    def test_varios_registros_ranking_filtrado(self):
        self.edge_client.post(
            '/api/registros/',
            {'dorsal': 1, 'tiempo_ms': 120000, 'confianza_ocr': 99.0},
            HTTP_AUTHORIZATION=self.auth_header
        )
        self.edge_client.post(
            '/api/registros/',
            {'dorsal': 2, 'tiempo_ms': 100000, 'confianza_ocr': 40.0},
            HTTP_AUTHORIZATION=self.auth_header
        )

        validados = RegistroTiempo.objects.filter(estado='validado').count()
        pendientes = RegistroTiempo.objects.filter(estado='pendiente').count()
        self.assertEqual(validados, 1)
        self.assertEqual(pendientes, 1)