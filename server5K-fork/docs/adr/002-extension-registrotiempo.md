# ADR-002: Extensión de RegistroTiempo vs Modelo Separado

**Fecha:** 2026-06-21
**Estado:** Aceptado
**Decisión:** Extender el modelo `RegistroTiempo` existente con nuevos campos de trazabilidad en lugar de crear un modelo separado `RegistroTiempoEdge`.

## Contexto

La nueva funcionalidad requiere que cada registro de tiempo incluya metadatos de trazabilidad: origen (automático/manual), confianza OCR, evidencia de imagen, estado de validación, dorsal detectado/corregido, motivo de descalificación y auditoría de validación.

## Opciones Consideradas

1. **Modelo separado `RegistroTiempoEdge`** - Nuevo modelo independiente para registros del Edge, manteniendo `RegistroTiempo` para registros manuales.
2. **Extender `RegistroTiempo`** - Agregar los nuevos campos como nullable al modelo existente.

## Decisión

Se eligió **extender el modelo existente** por las siguientes razones:

- **Unicidad conceptual**: Un registro de tiempo es lo mismo sin importar su origen. La clasificación y resultados se calculan sobre el mismo conjunto de datos.
- **Sin duplicación de lógica**: Métodos como `save()` (cálculo horas/minutos/segundos), `total_time()`, `average_time()` se mantienen en un solo lugar.
- **Migración simple**: Campos nuevos nullable no afectan registros existentes. En este proyecto no hay datos previos que migrar (BD desde cero).
- **Consultas unificadas**: `ResultsService` filtra por `estado__in=['validado','corregido']` sin necesidad de UNION entre dos tablas.

## Consecuencias

- Se agregaron 9 campos al modelo `RegistroTiempo`: `origen`, `confianza_ocr`, `evidencia_imagen`, `estado`, `dorsal_detectado`, `dorsal_corregido`, `motivo_descalificacion`, `validado_por` (FK→Juez), `validado_en`.
- Se agregó índice `(estado, created_at)` para optimizar consultas de registros pendientes.
- Los registros existentes (si los hubiera) mantienen valores default: `origen='manual'`, `estado='validado'`.
