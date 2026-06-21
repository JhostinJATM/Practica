# Especificación: Validación Manual por Jueces

## ADDED Requirements

### Requirement: Registro público de jueces

El sistema SHALL proveer una página web pública donde nuevos jueces puedan registrarse con `username`, `password`, `first_name`, `last_name` y `email`. El registro DEBE crear un `User` de Django vinculado 1:1 con un perfil `Juez`.

#### Scenario: Juez se registra exitosamente

- **WHEN** un usuario completa el formulario de registro con datos válidos
- **THEN** el sistema crea un `User` y un perfil `Juez` asociado
- **THEN** el sistema redirige al panel de validación con sesión iniciada

#### Scenario: Registro con username duplicado

- **WHEN** un usuario intenta registrarse con un `username` ya existente
- **THEN** el sistema muestra un mensaje de error "El nombre de usuario ya existe"
- **THEN** no se crea ningún registro nuevo

#### Scenario: Registro con contraseña insegura

- **WHEN** un usuario intenta registrarse con una contraseña de menos de 12 caracteres
- **THEN** el sistema muestra un mensaje de error indicando la longitud mínima requerida

### Requirement: Autenticación de jueces

El sistema SHALL permitir a los jueces iniciar sesión mediante `username` y `password` en una página de login. La sesión DEBE mantenerse con el sistema estándar de Django.

#### Scenario: Juez inicia sesión exitosamente

- **WHEN** un juez registrado ingresa `username` y `password` correctos
- **THEN** el sistema autentica al juez y redirige al panel de validación

#### Scenario: Credenciales inválidas

- **WHEN** un usuario ingresa `username` o `password` incorrectos
- **THEN** el sistema muestra "Credenciales inválidas" y permanece en la página de login

### Requirement: Panel de validación de registros pendientes

El sistema SHALL proveer un panel web donde los jueces autenticados visualicen los registros con `estado="pendiente"` de la competencia activa. El panel DEBE mostrar: dorsal detectado, confianza OCR, tiempo registrado, evidencia de imagen (si existe) y timestamp.

#### Scenario: Juez ve lista de registros pendientes

- **WHEN** un juez autenticado accede al panel de validación
- **THEN** el sistema muestra una lista de registros con `estado="pendiente"` de la competencia activa
- **THEN** cada registro muestra dorsal detectado, confianza OCR, tiempo y evidencia

#### Scenario: Panel muestra indicador cuando no hay evidencia

- **WHEN** un registro pendiente fue enviado por el Simulador sin imagen
- **THEN** el panel muestra un indicador "Sin evidencia de imagen" en lugar de la imagen

#### Scenario: Panel se actualiza en tiempo real vía WebSocket

- **WHEN** un nuevo registro pendiente es creado mientras el juez está en el panel
- **THEN** el registro aparece automáticamente en la lista sin necesidad de recargar la página

### Requirement: Confirmar dorsal

El sistema SHALL permitir al juez confirmar un registro pendiente, cambiando su `estado` a `"validado"`. Esta acción DEBE registrar: `validado_por` con el juez que confirma y `validado_en` con el timestamp.

#### Scenario: Juez confirma dorsal correcto

- **WHEN** un juez hace clic en "Confirmar" sobre un registro pendiente
- **THEN** el sistema cambia `estado` a `"validado"`, asigna `validado_por` al juez y `validado_en` al timestamp actual
- **THEN** el registro desaparece de la lista de pendientes

### Requirement: Corregir dorsal

El sistema SHALL permitir al juez corregir el dorsal de un registro pendiente. El dorsal original DEBE preservarse en `dorsal_detectado` y el nuevo valor en `dorsal_corregido`. El `estado` DEBE cambiar a `"corregido"`.

#### Scenario: Juez corrige dorsal incorrecto

- **WHEN** un juez ingresa un nuevo número de dorsal y hace clic en "Corregir"
- **THEN** el sistema cambia `dorsal_corregido` al nuevo valor, mantiene `dorsal_detectado` con el original
- **THEN** el sistema cambia `estado` a `"corregido"`
- **THEN** el sistema re-resuelve el equipo usando el dorsal corregido

#### Scenario: Dorsal corregido no existe en la competencia

- **WHEN** el juez ingresa un dorsal que no pertenece a ningún equipo de la competencia
- **THEN** el sistema muestra error "El dorsal corregido no pertenece a ningún equipo" y no aplica el cambio

### Requirement: Descalificar participante

El sistema SHALL permitir al juez descalificar un registro pendiente, cambiando su `estado` a `"descalificado"`. El juez DEBE ingresar obligatoriamente el `motivo_descalificacion`. El sistema DEBE rechazar la acción si el motivo está vacío.

#### Scenario: Juez descalifica con motivo válido

- **WHEN** un juez ingresa un motivo de descalificación y hace clic en "Descalificar"
- **THEN** el sistema cambia `estado` a `"descalificado"` y almacena el `motivo_descalificacion`
- **THEN** el registro sale de la lista de pendientes

#### Scenario: Descalificación sin motivo es rechazada

- **WHEN** un juez intenta descalificar sin escribir un motivo
- **THEN** el sistema muestra error "El motivo de descalificación es obligatorio"
- **THEN** el `estado` del registro permanece como `"pendiente"`

### Requirement: Trazabilidad del dorsal original

El sistema SHALL preservar siempre el `dorsal_detectado` original enviado por el Edge, incluso después de correcciones. Esto garantiza trazabilidad completa para auditoría.

#### Scenario: Dorsal original se preserva tras corrección

- **WHEN** un registro con `dorsal_detectado=42` es corregido a `dorsal_corregido=24`
- **THEN** el campo `dorsal_detectado` mantiene el valor `42`
- **THEN** el campo `dorsal_corregido` contiene `24`
