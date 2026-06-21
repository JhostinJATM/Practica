from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from app.models import RegistroTiempo, Equipo


class ValidacionService:

    def confirmar_registro(self, registro_id, juez) -> Dict[str, Any]:
        try:
            with transaction.atomic():
                registro = RegistroTiempo.objects.select_for_update().get(record_id=registro_id)

                if registro.estado != 'pendiente':
                    return {'exito': False, 'error': 'El registro no esta pendiente de validacion'}

                valor_anterior = {'estado': registro.estado}
                registro.estado = 'validado'
                registro.validado_por = juez
                registro.validado_en = timezone.now()
                registro.save(update_fields=['estado', 'validado_por', 'validado_en'])
                valor_nuevo = {'estado': registro.estado}

                self._registrar_auditoria(registro, juez, 'confirmar', valor_anterior, valor_nuevo)

                return {'exito': True, 'registro': registro}

        except RegistroTiempo.DoesNotExist:
            return {'exito': False, 'error': 'Registro no encontrado'}

    def corregir_dorsal(self, registro_id, juez, dorsal_corregido: int) -> Dict[str, Any]:
        try:
            with transaction.atomic():
                registro = RegistroTiempo.objects.select_for_update().get(record_id=registro_id)

                if registro.estado != 'pendiente':
                    return {'exito': False, 'error': 'El registro no esta pendiente de validacion'}

                competencia = registro.team.competition
                try:
                    nuevo_equipo = Equipo.objects.get(competition=competencia, number=dorsal_corregido)
                except Equipo.DoesNotExist:
                    return {'exito': False, 'error': 'El dorsal corregido no pertenece a ningun equipo'}

                valor_anterior = {
                    'estado': registro.estado,
                    'dorsal_detectado': registro.dorsal_detectado,
                }
                registro.dorsal_corregido = dorsal_corregido
                registro.estado = 'corregido'
                registro.team = nuevo_equipo
                registro.validado_por = juez
                registro.validado_en = timezone.now()
                registro.save()
                valor_nuevo = {
                    'estado': registro.estado,
                    'dorsal_corregido': dorsal_corregido,
                    'equipo_id': nuevo_equipo.id,
                }

                self._registrar_auditoria(registro, juez, 'corregir', valor_anterior, valor_nuevo)

                return {'exito': True, 'registro': registro}

        except RegistroTiempo.DoesNotExist:
            return {'exito': False, 'error': 'Registro no encontrado'}

    def descalificar_participante(self, registro_id, juez, motivo: str) -> Dict[str, Any]:
        if not motivo or not motivo.strip():
            return {'exito': False, 'error': 'El motivo de descalificacion es obligatorio'}

        try:
            with transaction.atomic():
                registro = RegistroTiempo.objects.select_for_update().get(record_id=registro_id)

                if registro.estado != 'pendiente':
                    return {'exito': False, 'error': 'El registro no esta pendiente de validacion'}

                valor_anterior = {'estado': registro.estado}
                registro.estado = 'descalificado'
                registro.motivo_descalificacion = motivo.strip()
                registro.validado_por = juez
                registro.validado_en = timezone.now()
                registro.save()
                valor_nuevo = {
                    'estado': registro.estado,
                    'motivo_descalificacion': motivo.strip(),
                }

                self._registrar_auditoria(registro, juez, 'descalificar', valor_anterior, valor_nuevo)

                return {'exito': True, 'registro': registro}

        except RegistroTiempo.DoesNotExist:
            return {'exito': False, 'error': 'Registro no encontrado'}

    def _registrar_auditoria(self, registro, juez, accion, valor_anterior, valor_nuevo):
        from app.models import AuditoriaRegistro
        AuditoriaRegistro.objects.create(
            registro_tiempo=registro,
            juez=juez,
            accion=accion,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
        )
