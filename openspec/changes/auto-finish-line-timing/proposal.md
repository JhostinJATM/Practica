## Why

El registro manual de tiempos por jueces cronometristas es lento, propenso a errores humanos y no escala en competencias con muchos participantes. Se necesita un sistema de visión por computadora que automatice la detección de cruces de meta, identifique dorsales por OCR y registre tiempos sin intervención humana. Los jueces pasan a un rol de supervisión: solo intervienen cuando la confianza del OCR es inferior al 95%.

## What Changes

- Nuevo modelo `RegistroTiempo` con trazabilidad completa: origen, confianza OCR, evidencia (imagen), estado y auditoría de acciones manuales.
- Nuevo modelo `Competencia` con token UUID autogenerado para autenticación de dispositivos Edge/simulador.
- Nuevo modelo `Juez` vinculado a `User` para gestión de validación manual.
- API REST para recepción de registros desde Edge/simulador (`POST /api/registros/`) con validación por token de competencia.
- WebSocket (Django Channels) para notificar registros pendientes a jueces y actualizar clasificación en tiempo real.
- Panel de validación para jueces: confirmar, corregir dorsal o descalificar registros con motivo obligatorio.
- Registro de auditoría para toda acción manual de jueces.
- Eliminación del flujo de registro manual de tiempos por cronometristas.
- Actualización en tiempo real de la página de resultados vía WebSocket.

## Capabilities

### New Capabilities

- `registro-tiempo-automatico`: Recepción de registros desde Edge/simulador, resolución de dorsal contra equipo y validación automática cuando OCR >= 95%.
- `validacion-manual`: Modelo Juez, registro público, autenticación y panel de validación de registros pendientes con acciones confirmar/corregir/descalificar.
- `token-competencia`: Generación automática de UUID por competencia, visible en administración, usado por Edge/simulador como `EDGE_TOKEN`.
- `clasificacion-tiempo-real`: Transmisión de actualizaciones de clasificación vía WebSocket a la página de resultados.
- `auditoria-registros`: Registro inmutable de toda acción manual de jueces (quién, qué, cuándo, valor anterior, valor nuevo).

### Modified Capabilities

<!-- No existen specs previas en openspec/specs/. Sin cambios a requisitos existentes. -->

## Impact

- **Modelos Django**: Nuevos modelos `RegistroTiempo`, `Juez`, y modificación de `Competencia` para incluir token UUID.
- **API REST**: Nuevo endpoint `POST /api/registros/` con autenticación por token. Nuevos endpoints para panel de jueces.
- **Dependencias nuevas**: Django Channels + Redis (o Daphne) para WebSocket.
- **Templates Django**: Nuevo panel de validación de jueces. Modificación de página de resultados para actualización en tiempo real.
- **Base de datos**: Migraciones nuevas sobre PostgreSQL 16 (creación desde cero).
- **Proyectos externos**: `rasc-vision-edge` y `simulador` son repos independientes que consumen la API. No se modifican en este repositorio.

## Non-goals

- No se implementa el procesamiento de visión por computadora en este repositorio (eso reside en `rasc-vision-edge`).
- No se implementa el simulador en este repositorio (es proyecto independiente).
- No se migran datos históricos (la base de datos se crea desde cero).
- No se modifica el flujo de inscripción de equipos/participantes existente.
- No se implementa streaming de video ni RTSP en el backend.
