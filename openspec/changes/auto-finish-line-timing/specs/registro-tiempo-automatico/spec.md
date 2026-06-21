# Especificación: Registro de Tiempo Automático

## ADDED Requirements

### Requirement: Recepción de registros desde Edge o Simulador

El sistema SHALL exponer un endpoint `POST /api/registros/` que reciba registros de tiempo desde dispositivos Edge o el Simulador. El endpoint DEBE aceptar autenticación mediante token de competencia en el header `Authorization: Token <uuid>`.

#### Scenario: Edge envía registro con token válido y dorsal existente

- **WHEN** el Edge envía `POST /api/registros/` con header `Authorization: Token <uuid>`, dorsal `42`, `tiempo_ms=125000` y `confianza_ocr=98.5`
- **THEN** el sistema resuelve el dorsal contra el `Equipo.number` de la competencia asociada al token
- **THEN** el sistema crea un `RegistroTiempo` con `origen="automatico"`, `estado="validado"`, `confianza_ocr=98.5`, `dorsal_detectado=42`
- **THEN** el sistema responde con HTTP 201 y el objeto JSON del registro creado incluyendo `equipo_id` resuelto

#### Scenario: Simulador envía registro sin imagen de evidencia

- **WHEN** el Simulador envía `POST /api/registros/` con `dorsal=15`, `tiempo_ms=89000`, `confianza_ocr=97.0` y sin campo `evidencia_imagen`
- **THEN** el sistema crea el registro con `evidencia_imagen=null` y `estado="validado"`
- **THEN** el sistema responde con HTTP 201

### Requirement: Validación del token de competencia

El sistema SHALL validar que el token enviado corresponda a una competencia activa. Si el token no existe o la competencia no está activa, el sistema DEBE rechazar la solicitud con HTTP 400.

#### Scenario: Token no corresponde a ninguna competencia

- **WHEN** el Edge envía un registro con un token UUID que no existe en el sistema
- **THEN** el sistema responde con HTTP 400 y mensaje `{"error": "Token invalido o competencia no activa"}`

#### Scenario: Competencia asociada al token no está activa

- **WHEN** el Edge envía un registro con un token de una competencia cuyo `is_active=false`
- **THEN** el sistema responde con HTTP 400 y mensaje `{"error": "Token invalido o competencia no activa"}`

### Requirement: Resolución de dorsal contra equipo

El sistema SHALL resolver el número de dorsal contra `Equipo.number` dentro de la competencia identificada por el token. Si el dorsal no coincide con ningún equipo, el sistema DEBE rechazar con HTTP 400.

#### Scenario: Dorsal no encontrado en la competencia

- **WHEN** el Edge envía un registro con `dorsal=999` y dicho dorsal no existe en la competencia activa
- **THEN** el sistema responde con HTTP 400 y mensaje `{"error": "Dorsal no encontrado en la competencia activa"}`

#### Scenario: Dorsal pertenece a equipo en la competencia correcta

- **WHEN** el Edge envía `dorsal=7` y existe un `Equipo` con `number=7` en la competencia del token
- **THEN** el sistema asocia el registro al equipo encontrado

### Requirement: Validación automática por confianza OCR

El sistema SHALL validar automáticamente los registros cuya `confianza_ocr` sea mayor o igual al 95%. Estos registros DEBEN crearse con `origen="automatico"` y `estado="validado"`.

#### Scenario: OCR con confianza suficiente genera registro validado

- **WHEN** el sistema recibe un registro con `confianza_ocr=95.0`
- **THEN** el sistema crea `RegistroTiempo` con `origen="automatico"`, `estado="validado"`

#### Scenario: OCR con confianza del 100% se auto-valida

- **WHEN** el sistema recibe un registro con `confianza_ocr=100.0`
- **THEN** el sistema crea `RegistroTiempo` con `origen="automatico"`, `estado="validado"`

### Requirement: Registro pendiente por confianza OCR baja

El sistema SHALL crear registros con `origen="manual"` y `estado="pendiente"` cuando la `confianza_ocr` sea inferior al 95%. Estos registros DEBEN ser visibles en el panel de validación de jueces.

#### Scenario: OCR con confianza baja genera registro pendiente

- **WHEN** el sistema recibe un registro con `confianza_ocr=94.9`
- **THEN** el sistema crea `RegistroTiempo` con `origen="manual"`, `estado="pendiente"`

#### Scenario: OCR con 0% de confianza genera registro pendiente

- **WHEN** el sistema recibe un registro con `confianza_ocr=0.0`
- **THEN** el sistema crea `RegistroTiempo` con `origen="manual"`, `estado="pendiente"`

### Requirement: Almacenamiento de evidencia de imagen

El sistema SHALL almacenar la imagen de evidencia enviada por el Edge como `ImageField`. Si el registro proviene del Simulador y no incluye imagen, el campo DEBE quedar `null`.

#### Scenario: Edge real envía imagen JPEG en base64

- **WHEN** el Edge envía un registro con `evidencia_imagen` como JPEG codificado en base64
- **THEN** el sistema decodifica y almacena la imagen en el `ImageField`
- **THEN** el registro tiene `evidencia_imagen` no nula accesible vía URL

#### Scenario: Simulador no envía imagen

- **WHEN** el Simulador envía un registro sin el campo `evidencia_imagen`
- **THEN** el sistema almacena `evidencia_imagen=null`

### Requirement: Notificación WebSocket de registro pendiente

El sistema SHALL notificar a los jueces conectados vía WebSocket cuando se cree un registro con `estado="pendiente"`. La notificación DEBE incluir el `record_id`, dorsal detectado, tiempo y confianza OCR.

#### Scenario: Juez conectado recibe notificación de registro pendiente

- **WHEN** se crea un registro con `estado="pendiente"` en una competencia
- **THEN** los jueces conectados al WebSocket de esa competencia reciben un mensaje `tipo="registro_pendiente"` con los datos del registro

#### Scenario: Sin jueces conectados no hay error

- **WHEN** se crea un registro pendiente y no hay jueces conectados al WebSocket
- **THEN** el sistema continúa sin errores y el registro queda disponible en el panel de validación

### Requirement: Respuesta del endpoint de registro

El sistema SHALL responder con HTTP 201 y el objeto JSON del registro creado. La respuesta DEBE incluir `record_id`, `estado` resultante, `equipo_id` resuelto y `equipo_nombre`.

#### Scenario: Respuesta exitosa incluye datos completos

- **WHEN** el sistema procesa exitosamente un registro
- **THEN** la respuesta incluye `{"record_id": "<uuid>", "estado": "validado", "equipo_id": 5, "equipo_nombre": "Los Veloces", "dorsal_detectado": 42, "tiempo_ms": 125000}`
