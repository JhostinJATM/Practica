# Especificación: Auditoría de Registros

## ADDED Requirements

### Requirement: Registro de auditoría por acción manual

El sistema SHALL crear un registro en `AuditoriaRegistro` cada vez que un juez realice una acción manual sobre un `RegistroTiempo` (confirmar, corregir o descalificar). El registro DEBE incluir: `registro_tiempo_id`, `juez_id`, `accion`, `valor_anterior` (JSON), `valor_nuevo` (JSON) y `creado_en`.

#### Scenario: Auditoría registra acción de confirmar

- **WHEN** un juez confirma un registro pendiente
- **THEN** el sistema crea un `AuditoriaRegistro` con `accion="confirmar"`, `valor_anterior={"estado": "pendiente"}`, `valor_nuevo={"estado": "validado"}`

#### Scenario: Auditoría registra acción de corregir

- **WHEN** un juez corrige un dorsal de `42` a `24`
- **THEN** el sistema crea un `AuditoriaRegistro` con `accion="corregir"`, `valor_anterior` conteniendo `dorsal_detectado=42`, `valor_nuevo` conteniendo `dorsal_corregido=24`

#### Scenario: Auditoría registra acción de descalificar

- **WHEN** un juez descalifica un registro con motivo "Fuera de carril"
- **THEN** el sistema crea un `AuditoriaRegistro` con `accion="descalificar"`, `valor_anterior={"estado": "pendiente"}`, `valor_nuevo={"estado": "descalificado", "motivo": "Fuera de carril"}`

### Requirement: Inmutabilidad de los registros de auditoría

El sistema SHALL garantizar que los registros de `AuditoriaRegistro` sean inmutables una vez creados. No DEBE existir ningún endpoint ni método que permita modificar o eliminar un registro de auditoría.

#### Scenario: Registro de auditoría no puede editarse

- **WHEN** se intenta modificar un `AuditoriaRegistro` existente por cualquier medio
- **THEN** el sistema rechaza la operación

#### Scenario: Registro de auditoría no puede eliminarse

- **WHEN** se intenta eliminar un `AuditoriaRegistro`
- **THEN** el sistema rechaza la operación

### Requirement: Asociación de auditoría al registro original

Cada `AuditoriaRegistro` DEBE estar vinculado mediante FK al `RegistroTiempo` sobre el cual se realizó la acción. Esto permite consultar el historial completo de acciones sobre un registro.

#### Scenario: Historial de auditoría consultable por registro

- **WHEN** se consultan las auditorías asociadas a un `RegistroTiempo` específico
- **THEN** el sistema retorna todas las acciones realizadas sobre ese registro, ordenadas por `creado_en` descendente

### Requirement: Auditoría incluye identidad del juez

Cada `AuditoriaRegistro` DEBE vincularse al `Juez` que realizó la acción mediante FK. Esto garantiza trazabilidad completa de quién realizó cada acción.

#### Scenario: Auditoría identifica al juez responsable

- **WHEN** se consulta un registro de auditoría
- **THEN** incluye el `username`, `first_name` y `last_name` del juez que realizó la acción

### Requirement: Campos JSON para flexibilidad

Los campos `valor_anterior` y `valor_nuevo` del modelo `AuditoriaRegistro` DEBEN ser de tipo JSON para capturar cualquier cambio en los campos relevantes del `RegistroTiempo` sin necesidad de modificar el esquema.

#### Scenario: JSON captura múltiples campos modificados

- **WHEN** un juez corrige el dorsal y además el sistema actualiza `estado` y `validado_por`
- **THEN** `valor_nuevo` contiene todos los campos modificados en estructura JSON
- **THEN** `valor_anterior` contiene los valores previos a la modificación
