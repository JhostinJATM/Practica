"""
Módulo: registro_views
Vistas API REST para el registro de tiempos.
Implementa endpoints HTTP para enviar registros (más confiable que WebSocket).
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import uuid
import logging

from app.models import Equipo, RegistroTiempo, Juez, Competencia
from app.auth.authentication import EdgeTokenAuth

logger = logging.getLogger(__name__)


class RegistrarTiemposView(APIView):
    """
    POST /api/equipos/{equipo_id}/registros/
    
    Registra los 15 tiempos de un equipo de manera atómica.
    Solo el juez asignado al equipo puede enviar registros.
    
    Request Body:
    {
        "registros": [
            {
                "id_registro": "uuid-opcional",
                "tiempo": 125000,
                "horas": 0,
                "minutos": 2,
                "segundos": 5,
                "milisegundos": 0
            },
            ...
        ]
    }
    
    Response (201 Created):
    {
        "exito": true,
        "mensaje": "Registros guardados exitosamente",
        "equipo_id": 1,
        "equipo_nombre": "Los Veloces",
        "total_guardados": 15,
        "registros": [...]
    }
    """
    
    permission_classes = [IsAuthenticated]
    MAX_REGISTROS = 15
    
    def post(self, request, equipo_id):
        juez = request.user
        
        logger.info(f"[HTTP] Juez {juez.username} enviando registros para equipo {equipo_id}")
        
        # Validar que el usuario sea un Juez
        if not isinstance(juez, Juez):
            try:
                juez = Juez.objects.get(id=juez.id)
            except Juez.DoesNotExist:
                return Response(
                    {"exito": False, "error": "Usuario no es un juez válido"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Obtener registros del body
        registros = request.data.get('registros', [])
        
        if not registros:
            return Response(
                {"exito": False, "error": "No se enviaron registros"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # VALIDACIÓN ESTRICTA: Deben ser exactamente 15 registros
        if len(registros) != self.MAX_REGISTROS:
            return Response(
                {"exito": False, "error": f"Se requieren exactamente {self.MAX_REGISTROS} registros. Recibidos: {len(registros)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Verificar que el juez tenga equipos asignados
                equipos_juez = juez.teams.select_related('competition').all()
                if not equipos_juez.exists():
                    return Response(
                        {"exito": False, "error": "No tienes equipos asignados"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Verificar que la competencia esté en curso
                competencia = equipos_juez.first().competition
                if not competencia or not competencia.is_running:
                    return Response(
                        {"exito": False, "error": "La competencia no está en curso"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Obtener el equipo y verificar pertenencia
                try:
                    equipo = Equipo.objects.select_for_update().get(id=equipo_id)
                except Equipo.DoesNotExist:
                    return Response(
                        {"exito": False, "error": f"Equipo {equipo_id} no existe"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if equipo.judge_id != juez.id:
                    return Response(
                        {"exito": False, "error": "Este equipo no te pertenece"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Delegar creación en el servicio (usa bulk_create + idempotencia)
                from app.services.registro_service import RegistroService
                servicio = RegistroService()
                # Usar versión SÍNCRONA para evitar problemas de conexión en vistas HTTP
                resultado = servicio.registrar_batch_sync(juez=juez, equipo_id=equipo.id, registros=registros)

                logger.info(
                    "[HTTP] Registros procesados: guardados=%s fallidos=%s equipo=%s(%s) juez=%s(%s)",
                    resultado['total_guardados'],
                    resultado['total_fallidos'],
                    equipo.name,
                    equipo.id,
                    juez.username,
                    juez.id,
                )

                if resultado['total_guardados'] == 0 and resultado['total_fallidos'] > 0:
                    return Response({"exito": False, "error": resultado['registros_fallidos']}, status=status.HTTP_400_BAD_REQUEST)

                # Notificar por WebSocket a la UI pública
                self._notificar_actualizacion(equipo, resultado['registros_guardados'])
                
                return Response({
                    "exito": True,
                    "mensaje": "Registros guardados exitosamente",
                    "equipo_id": equipo.id,
                    "equipo_nombre": equipo.name,
                    "equipo_dorsal": equipo.number,
                    "total_guardados": resultado['total_guardados'],
                    "registros": resultado['registros_guardados'],
                    "registros_fallidos": resultado['registros_fallidos'],
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"[HTTP] Error guardando registros: {str(e)}")
            return Response(
                {"exito": False, "error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _notificar_actualizacion(self, equipo, registros):
        """
        Notifica a los clientes conectados que hay nuevos registros.
        Esto permite actualizar la UI pública en tiempo real.
        """
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                competencia_group = f'competencia_{equipo.competition_id}'
                
                # Calcular tiempo total
                tiempo_total = sum(r['tiempo'] for r in registros if not r.get('duplicado', False))
                
                async_to_sync(channel_layer.group_send)(
                    competencia_group,
                    {
                        'type': 'registros_actualizados',
                        'data': {
                            'equipo_id': equipo.id,
                            'equipo_nombre': equipo.name,
                            'equipo_dorsal': equipo.number,
                            'total_registros': len(registros),
                            'tiempo_total': tiempo_total,
                        }
                    }
                )
                logger.info(f"[WS] Notificación enviada al grupo {competencia_group}")
        except Exception as e:
            logger.warning(f"[WS] No se pudo notificar por WebSocket: {e}")


class EstadoEquipoRegistrosView(APIView):
    """
    GET /api/equipos/{equipo_id}/registros/estado/
    
    Verifica el estado de registros de un equipo.
    Útil para saber si ya se enviaron los tiempos.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, equipo_id):
        juez = request.user
        
        try:
            equipo = Equipo.objects.get(id=equipo_id)
        except Equipo.DoesNotExist:
            return Response(
                {"error": "Equipo no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Contar registros
        total_registros = RegistroTiempo.objects.filter(team=equipo).count()
        
        # Obtener registros ordenados
        registros = RegistroTiempo.objects.filter(team=equipo).order_by('time')
        
        registros_data = [{
            'id_registro': str(r.record_id),
            'tiempo': r.time,
            'horas': r.hours,
            'minutos': r.minutes,
            'segundos': r.seconds,
            'milisegundos': r.milliseconds,
        } for r in registros]
        
        return Response({
            "equipo_id": equipo.id,
            "equipo_nombre": equipo.name,
            "total_registros": total_registros,
            "maximo_registros": 15,
            "puede_enviar": total_registros == 0,
            "registros": registros_data
        })


class EdgeRegistroView(APIView):
    """
    POST /api/registros/

    Recibe registros de tiempo desde dispositivos Edge o el Simulador.
    Autenticacion por token de competencia (header Authorization: Token <uuid>).

    Request Body:
    {
        "dorsal": 42,
        "tiempo_ms": 125000,
        "confianza_ocr": 98.5,
        "evidencia_imagen": "<base64>"  // opcional
    }

    Response (201):
    {
        "record_id": "<uuid>",
        "estado": "validado",
        "equipo_id": 5,
        "equipo_nombre": "Los Veloces",
        "dorsal_detectado": 42,
        "tiempo_ms": 125000
    }
    """

    authentication_classes = [EdgeTokenAuth]
    permission_classes = []

    def post(self, request):
        from app.serializers.serializers import EdgeRegistroSerializer

        if not hasattr(request.user, 'is_running'):
            return Response(
                {"error": "Token de autorizacion requerido"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = EdgeRegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Datos invalidos", "detalles": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        competencia = request.user
        dorsal = serializer.validated_data['dorsal']
        tiempo_ms = serializer.validated_data['tiempo_ms']
        confianza_ocr = serializer.validated_data['confianza_ocr']
        evidencia_b64 = serializer.validated_data.get('evidencia_imagen')

        if not competencia.is_running:
            return Response(
                {"error": "La competencia no esta en curso"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            equipo = Equipo.objects.get(
                competition=competencia,
                number=dorsal
            )
        except Equipo.DoesNotExist:
            return Response(
                {"error": "Dorsal no encontrado en la competencia activa"},
                status=status.HTTP_400_BAD_REQUEST
            )

        es_automatico = float(confianza_ocr) >= 95.0
        estado = "validado" if es_automatico else "pendiente"
        origen = "automatico" if es_automatico else "manual"

        logger.info(
            "[EdgeRegistro] dorsal=%s tiempo=%sms confianza=%.2f -> %s",
            dorsal, tiempo_ms, confianza_ocr, estado
        )

        hora_total = tiempo_ms
        horas = hora_total // 3600000
        minutos = (hora_total % 3600000) // 60000
        segundos = (hora_total % 60000) // 1000
        milisegundos = hora_total % 1000

        registro = RegistroTiempo(
            team=equipo,
            time=tiempo_ms,
            hours=horas,
            minutes=minutos,
            seconds=segundos,
            milliseconds=milisegundos,
            origen=origen,
            confianza_ocr=confianza_ocr,
            estado=estado,
            dorsal_detectado=dorsal,
        )

        if evidencia_b64:
            import base64
            import uuid as uuid_mod
            from django.core.files.base import ContentFile
            try:
                imagen_data = base64.b64decode(evidencia_b64)
                filename = f"evidencia_{uuid_mod.uuid4().hex[:12]}.jpg"
                registro.evidencia_imagen.save(filename, ContentFile(imagen_data), save=False)
            except Exception:
                pass

        registro.save()

        if estado == "validado":
            self._notificar_clasificacion(competencia, equipo)
        else:
            self._notificar_pendiente(competencia, registro)

        response_data = {
            "record_id": str(registro.record_id),
            "estado": estado,
            "equipo_id": equipo.id,
            "equipo_nombre": equipo.name,
            "dorsal_detectado": dorsal,
            "tiempo_ms": tiempo_ms,
            "confianza_ocr": confianza_ocr,
        }
        if not es_automatico:
            response_data["mensaje"] = "Registro pendiente de validacion por OCR < 95%"

        return Response(response_data, status=status.HTTP_201_CREATED)

    def _notificar_clasificacion(self, competencia, equipo):
        from app.services.registro_service import RegistroService
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                group = f'competencia_{competencia.id}'
                async_to_sync(channel_layer.group_send)(
                    group,
                    {
                        'type': 'registros_actualizados',
                        'data': {
                            'equipo_id': equipo.id,
                            'equipo_nombre': equipo.name,
                            'equipo_dorsal': equipo.number,
                            'tiempo_total': sum(
                                RegistroTiempo.objects.filter(team=equipo, estado__in=['validado', 'corregido'])
                                .values_list('time', flat=True)
                            ),
                        }
                    }
                )
        except Exception as e:
            logger.warning(f"[EdgeRegistro] No se pudo notificar clasificacion: {e}")

    def _notificar_pendiente(self, competencia, registro):
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                group = f'validacion_{competencia.id}'
                async_to_sync(channel_layer.group_send)(
                    group,
                    {
                        'type': 'registro_pendiente',
                        'data': {
                            'record_id': str(registro.record_id),
                            'dorsal_detectado': registro.dorsal_detectado,
                            'tiempo_ms': registro.time,
                            'confianza_ocr': registro.confianza_ocr,
                            'equipo_id': registro.team_id,
                            'equipo_nombre': registro.team.name,
                            'estado': 'pendiente',
                            'created_at': registro.created_at.isoformat(),
                        }
                    }
                )
                logger.info(f"[EdgeRegistro] Notificacion pendiente enviada a validacion_{competencia.id}")
        except Exception as e:
            logger.warning(f"[EdgeRegistro] No se pudo notificar registro pendiente: {e}")


class ValidacionPendientesView(APIView):
    """
    GET /api/validacion/pendientes/

    Lista los registros pendientes de validacion para la competencia activa.
    Requiere que el usuario tenga perfil de juez.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = []

    def get(self, request):
        from app.models import Competencia
        from app.views.auth_views import IsJudgeAuthenticated

        permiso = IsJudgeAuthenticated()
        if not permiso.has_permission(request, self):
            return Response({"error": "Acceso denegado"}, status=status.HTTP_403_FORBIDDEN)

        juez = request.user.perfil_juez
        competencia_activa = Competencia.objects.filter(is_active=True, is_running=True).first()

        if not competencia_activa:
            return Response({
                "pendientes": [],
                "mensaje": "No hay competencia activa en este momento"
            })

        registros = RegistroTiempo.objects.filter(
            team__competition=competencia_activa,
            estado='pendiente'
        ).select_related('team').order_by('-created_at')

        data = [{
            'record_id': str(r.record_id),
            'dorsal_detectado': r.dorsal_detectado,
            'tiempo_ms': r.time,
            'confianza_ocr': r.confianza_ocr,
            'equipo_nombre': r.team.name,
            'equipo_dorsal': r.team.number,
            'evidencia_url': request.build_absolute_uri(r.evidencia_imagen.url) if r.evidencia_imagen else None,
            'created_at': r.created_at.isoformat(),
            'estado': r.estado,
        } for r in registros]

        return Response({"pendientes": data, "competencia": competencia_activa.name})


class ConfirmarRegistroView(APIView):
    """POST /api/validacion/{record_id}/confirmar/"""

    authentication_classes = [SessionAuthentication]
    permission_classes = []

    def post(self, request, record_id):
        from app.views.auth_views import IsJudgeAuthenticated
        from app.services.validacion_service import ValidacionService

        permiso = IsJudgeAuthenticated()
        if not permiso.has_permission(request, self):
            return Response({"error": "Acceso denegado"}, status=status.HTTP_403_FORBIDDEN)

        juez = request.user.perfil_juez
        service = ValidacionService()
        resultado = service.confirmar_registro(record_id, juez)

        if not resultado['exito']:
            return Response({"error": resultado['error']}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "mensaje": "Registro confirmado exitosamente",
            "record_id": str(resultado['registro'].record_id),
            "estado": resultado['registro'].estado,
        })


class CorregirDorsalView(APIView):
    """POST /api/validacion/{record_id}/corregir/"""

    authentication_classes = [SessionAuthentication]
    permission_classes = []

    def post(self, request, record_id):
        from app.views.auth_views import IsJudgeAuthenticated
        from app.services.validacion_service import ValidacionService
        from app.serializers.serializers import ValidacionCorregirSerializer

        permiso = IsJudgeAuthenticated()
        if not permiso.has_permission(request, self):
            return Response({"error": "Acceso denegado"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ValidacionCorregirSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Datos invalidos", "detalles": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        juez = request.user.perfil_juez
        dorsal_corregido = serializer.validated_data['dorsal_corregido']
        service = ValidacionService()
        resultado = service.corregir_dorsal(record_id, juez, dorsal_corregido)

        if not resultado['exito']:
            return Response({"error": resultado['error']}, status=status.HTTP_400_BAD_REQUEST)

        registro = resultado['registro']
        return Response({
            "mensaje": "Dorsal corregido exitosamente",
            "record_id": str(registro.record_id),
            "dorsal_detectado": registro.dorsal_detectado,
            "dorsal_corregido": registro.dorsal_corregido,
            "estado": registro.estado,
        })


class DescalificarParticipanteView(APIView):
    """POST /api/validacion/{record_id}/descalificar/"""

    authentication_classes = [SessionAuthentication]
    permission_classes = []

    def post(self, request, record_id):
        from app.views.auth_views import IsJudgeAuthenticated
        from app.services.validacion_service import ValidacionService
        from app.serializers.serializers import ValidacionDescalificarSerializer

        permiso = IsJudgeAuthenticated()
        if not permiso.has_permission(request, self):
            return Response({"error": "Acceso denegado"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ValidacionDescalificarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Datos invalidos", "detalles": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        juez = request.user.perfil_juez
        motivo = serializer.validated_data['motivo']
        service = ValidacionService()
        resultado = service.descalificar_participante(record_id, juez, motivo)

        if not resultado['exito']:
            return Response({"error": resultado['error']}, status=status.HTTP_400_BAD_REQUEST)

        registro = resultado['registro']
        return Response({
            "mensaje": "Participante descalificado exitosamente",
            "record_id": str(registro.record_id),
            "motivo": registro.motivo_descalificacion,
            "estado": registro.estado,
        })


class AuditoriaListView(APIView):
    """GET /api/auditoria/ - Lista el historial de auditoria."""

    def get(self, request):
        from app.models import AuditoriaRegistro

        registro_id = request.GET.get('registro_tiempo_id')
        queryset = AuditoriaRegistro.objects.select_related('juez', 'registro_tiempo').order_by('-creado_en')

        if registro_id:
            queryset = queryset.filter(registro_tiempo_id=registro_id)

        data = [{
            'id': a.id,
            'registro_tiempo_id': str(a.registro_tiempo_id),
            'juez_id': a.juez_id,
            'juez_username': a.juez.username,
            'accion': a.accion,
            'valor_anterior': a.valor_anterior,
            'valor_nuevo': a.valor_nuevo,
            'creado_en': a.creado_en.isoformat(),
        } for a in queryset[:100]]

        return Response({"total": queryset.count(), "auditorias": data})
