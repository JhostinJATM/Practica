# Especificación: Token de Competencia

## ADDED Requirements

### Requirement: Generación automática de token al crear competencia

El sistema SHALL generar automáticamente un token UUID v4 único al crear una nueva `Competencia`. El token DEBE almacenarse en el campo `token` del modelo y DEBE ser inmutable una vez generado.

#### Scenario: Token se genera al crear competencia

- **WHEN** un administrador crea una nueva competencia desde el panel de administración
- **THEN** el sistema asigna automáticamente un UUID v4 al campo `token`
- **THEN** el token es único en toda la base de datos

#### Scenario: Token no se modifica al editar la competencia

- **WHEN** un administrador edita el nombre o fecha de una competencia existente
- **THEN** el campo `token` permanece sin cambios

### Requirement: Visualización del token en administración

El sistema SHALL mostrar el token de competencia en el panel de administración de Django para que los operadores puedan copiarlo y configurarlo en los dispositivos Edge o el Simulador.

#### Scenario: Token visible en el detalle de competencia

- **WHEN** un administrador accede al detalle de una competencia en el panel de administración
- **THEN** el token UUID es visible y puede copiarse

#### Scenario: Token visible en la lista de competencias

- **WHEN** un administrador visualiza la lista de competencias
- **THEN** cada competencia muestra su token en una columna

### Requirement: Validación de token en peticiones Edge

El sistema SHALL autenticar las peticiones al endpoint `POST /api/registros/` verificando que el token en el header `Authorization: Token <uuid>` corresponda a una competencia con `is_active=true`.

#### Scenario: Token válido de competencia activa

- **WHEN** el Edge envía una petición con `Authorization: Token <uuid>` de una competencia `is_active=true`
- **THEN** el sistema acepta la petición y procesa el registro

#### Scenario: Token de competencia inactiva

- **WHEN** el Edge envía una petición con token de una competencia `is_active=false`
- **THEN** el sistema responde con HTTP 400 `{"error": "Token invalido o competencia no activa"}`

#### Scenario: Petición sin token

- **WHEN** se recibe una petición a `POST /api/registros/` sin header `Authorization`
- **THEN** el sistema responde con HTTP 401 `{"error": "Token de autorizacion requerido"}`

### Requirement: Unicidad del token

El sistema SHALL garantizar que cada competencia tenga un token único. No DEBEN existir dos competencias con el mismo token.

#### Scenario: Sistema garantiza unicidad

- **WHEN** se crean múltiples competencias
- **THEN** cada una recibe un token UUID diferente
- **THEN** no existen colisiones de tokens en la base de datos
