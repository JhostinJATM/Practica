## Context

El proyecto `server5k-fork` es una aplicación Django monolítica con una única app (`app`) que gestiona competencias atléticas. Actualmente los jueces cronometristas registran manualmente 15 tiempos por equipo vía HTTP/WebSocket. El sistema ya cuenta con Django Channels (Redis + Daphne) para notificaciones en tiempo real, autenticación JWT personalizada sobre el modelo `Juez`, y PostgreSQL 16.

Se requiere eliminar el registro manual e incorporar un flujo automático donde dispositivos Edge (proyecto independiente `rasc-vision-edge`) detecten cruces de meta por visión artificial, identifiquen dorsales con OCR y envíen registros al backend. Los jueces pasan a validar solo los registros con confianza OCR < 95%.

## Goals / Non-Goals

**Goals:**
- Recibir registros automáticos desde Edge/simulador vía API REST con autenticación por token de competencia (UUID).
- Resolver dorsales contra equipos y validar automáticamente registros con OCR >= 95%.
- Notificar registros pendientes (OCR < 95%) a jueces vía WebSocket en tiempo real.
- Proveer panel de validación para jueces: confirmar, corregir dorsal, o descalificar con motivo.
- Registrar auditoría inmutable de toda acción manual de jueces.
- Actualizar clasificación en tiempo real en la página de resultados.

**Non-Goals:**
- No se implementa procesamiento de visión (OpenCV/EasyOCR) en este repositorio.
- No se implementa el simulador ni el Edge en este repositorio.
- No se migran datos históricos.
- No se modifica el flujo de inscripción de equipos ni la asignación juez-equipo.

## Decisions

### 1. Extender `RegistroTiempo` con campos de trazabilidad (no crear modelo nuevo)

**Alternativa**: Crear `RegistroTiempoEdge` como modelo separado.
**Decisión**: Extender el modelo existente porque un registro es conceptualmente lo mismo sin importar su origen, y evita duplicar lógica de cálculo de tiempos. Los nuevos campos son nullable para mantener compatibilidad con registros manuales existentes.

**Campos nuevos en `RegistroTiempo`:**
| Campo | Tipo | Descripción |
|---|---|---|
| `origen` | CharField(choices) | `automatico` / `manual` |
| `confianza_ocr` | FloatField(null=True) | 0-100, nullable para registros manuales antiguos |
| `evidencia_imagen` | ImageField(null=True) | Imagen JPEG del cruce; null si proviene del simulador |
| `estado` | CharField(choices) | `validado` / `pendiente` / `corregido` / `descalificado` |
| `dorsal_detectado` | PositiveIntegerField(null=True) | Dorsal leído por OCR |
| `dorsal_corregido` | PositiveIntegerField(null=True) | Dorsal corregido por juez |
| `motivo_descalificacion` | TextField(blank=True) | Obligatorio si estado = `descalificado` |
| `validado_por` | FK→Juez(null=True) | Juez que validó (null si automático) |
| `validado_en` | DateTimeField(null=True) | Timestamp de validación |

### 2. Autenticación Edge: token de competencia como API Key (no JWT)

**Alternativa**: Usar JWT para Edge también.
**Decisión**: Token UUID simple en header `Authorization: Token <uuid>` porque:
- El Edge/simulador no necesita sesiones, solo identificar la competencia.
- Token ya está asociado 1:1 con una competencia (generado al crearla).
- Más simple de implementar en dispositivos Edge con recursos limitados.
- El backend valida que el token corresponda a una competencia activa.

### 3. Endpoint único para Edge (`POST /api/registros/`) en lugar de por equipo

**Alternativa**: `POST /api/equipos/{id}/registros/` como el endpoint de jueces.
**Decisión**: Endpoint único porque el Edge no conoce IDs de equipo, solo dorsales. El backend resuelve el dorsal contra `Equipo.number` filtrado por la competencia del token.

### 4. Modelo `AuditoriaRegistro` separado para trazabilidad de acciones manuales

Cada acción de juez (confirmar, corregir, descalificar) genera un registro inmutable con: `juez`, `registro`, `accion`, `valor_anterior`, `valor_nuevo`, `timestamp`. No se usa django-simple-history para mantener dependencias mínimas y control total.

### 5. WebSocket: nuevo grupo `validacion_{competencia_id}` para jueces

El `JuezConsumer` existente se une al grupo de validación de su competencia para recibir notificaciones `registro_pendiente` en tiempo real. No se crea un consumer nuevo.

### 6. Jueces: registro público con modelo `User` de Django

**Alternativa**: Extender el modelo `Juez` existente con campos de `User`.
**Decisión**: Crear un modelo `Juez` vinculado 1:1 con `django.contrib.auth.models.User`. El modelo `Juez` existente se mantiene pero el nuevo flujo usa `User` + perfil `Juez`. Esto permite usar el sistema de autenticación estándar de Django (login, logout, sesiones) para el panel web de validación.

### 7. Registro de auditoría inmutable

Cada acción manual de juez queda registrada en `AuditoriaRegistro` con los campos: `registro_tiempo` (FK), `juez` (FK), `accion` (choices), `valor_anterior` (JSON), `valor_nuevo` (JSON), `creado_en` (DateTime). Esto garantiza trazabilidad completa incluso si el registro original es modificado posteriormente.

## Arquitectura C4

### Nivel 1: Contexto del Sistema

```mermaid
C4Context
  title Diagrama de Contexto - RASC UNL Vision

  Person(juez, "Juez", "Valida registros con OCR < 95%")
  Person(espectador, "Espectador", "Consulta resultados en vivo")

  System(server5k, "server5k-fork", "Django + DRF + Channels", "Gestiona competencias, recibe registros Edge, sirve panel de validación y resultados en tiempo real")

  System_Ext(edge, "rasc-vision-edge", "Python + OpenCV + EasyOCR", "Detecta cruces de meta, identifica dorsales por OCR y envía registros al backend")
  System_Ext(simulador, "Simulador Edge", "Python + Tkinter", "Genera eventos sintéticos para desarrollo sin cámaras reales")
  System_Ext(camara, "Cámaras IP", "RTSP", "Proveen video en tiempo real al dispositivo Edge")

  Rel(edge, camara, "Consume video de", "RTSP")
  Rel(edge, server5k, "Envía registros de tiempo", "HTTP REST + Token UUID")
  Rel(simulador, server5k, "Envía registros sintéticos", "HTTP REST + Token UUID")
  Rel(juez, server5k, "Valida registros pendientes", "HTTPS + WebSocket")
  Rel(espectador, server5k, "Ve resultados en vivo", "HTTPS + WebSocket")
```

### Nivel 2: Contenedores

```mermaid
C4Container
  title Diagrama de Contenedores - server5k-fork

  Person(juez, "Juez", "Valida registros")
  Person(espectador, "Espectador", "Consulta resultados")

  System_Ext(edge, "rasc-vision-edge", "Python + OpenCV")
  System_Ext(simulador, "Simulador", "Python + Tkinter")

  System_Boundary(server5k, "server5k-fork") {
    Container(web, "Aplicación Web", "Django + DRF", "Sirve API REST, templates HTML y panel de validación")
    Container(ws, "Servidor WebSocket", "Django Channels + Daphne", "Notifica registros pendientes y clasificación en tiempo real")
    ContainerDb(db, "Base de Datos", "PostgreSQL 16", "Almacena competencias, equipos, registros, auditoría")
    ContainerDb(redis, "Redis", "Redis 7", "Channel layer para WebSocket y caché de clasificación")
  }

  Rel(edge, web, "POST /api/registros/", "HTTPS + Token")
  Rel(simulador, web, "POST /api/registros/", "HTTPS + Token")
  Rel(juez, web, "Valida registros", "HTTPS")
  Rel(juez, ws, "Recibe notificaciones", "WSS")
  Rel(espectador, web, "Ve resultados", "HTTPS")
  Rel(espectador, ws, "Recibe actualizaciones", "WSS")
  Rel(web, db, "Lee/escribe", "SQL")
  Rel(web, redis, "Publica/consume", "Redis Pub/Sub")
  Rel(ws, redis, "Publica/consume", "Redis Pub/Sub")
```

### Nivel 3: Componentes (Aplicación Django)

```mermaid
C4Component
  title Diagrama de Componentes - Aplicación Django

  Container_Boundary(app, "app (Django)") {
    Component(edge_view, "EdgeRegistroView", "DRF APIView", "POST /api/registros/ - Recibe registros del Edge")
    Component(validacion_view, "ValidacionViews", "DRF APIView", "GET/POST /api/validacion/ - Panel de jueces")
    Component(juez_auth, "JuezAuthViews", "DRF APIView", "Registro, login y perfil de jueces")
    Component(results_view, "ResultsViews", "Django View", "Página pública de resultados")

    Component(registro_svc, "RegistroService", "Python", "Lógica de negocio: procesar registros Edge, resolver dorsales, auto-validar")
    Component(validacion_svc, "ValidacionService", "Python", "Confirmar, corregir y descalificar registros con auditoría")
    Component(results_svc, "ResultsService", "Python", "Cálculo de ranking y clasificación por equipo")

    Component(edge_auth, "EdgeTokenAuth", "DRF Auth", "Autentica Edge/simulador por token UUID de competencia")
    Component(juez_jwt, "JuezJWTAuth", "SimpleJWT", "Autentica jueces por JWT")

    Component(juez_consumer, "JuezConsumer", "Channels", "WebSocket privado: notifica registros pendientes")
    Component(public_consumer, "CompetenciaPublicConsumer", "Channels", "WebSocket público: ranking en vivo")
  }

  ContainerDb(db, "PostgreSQL", "PostgreSQL 16", "Modelos: Competencia, Equipo, RegistroTiempo, AuditoriaRegistro")
  ContainerDb(redis, "Redis", "Redis 7", "Channel layer")

  Rel(edge_view, edge_auth, "Usa")
  Rel(edge_view, registro_svc, "Llama a")
  Rel(registro_svc, db, "Lee/escribe")
  Rel(registro_svc, redis, "Notifica por")
  Rel(validacion_view, juez_jwt, "Usa")
  Rel(validacion_view, validacion_svc, "Llama a")
  Rel(validacion_svc, db, "Lee/escribe")
  Rel(juez_consumer, juez_jwt, "Usa")
  Rel(juez_consumer, redis, "Suscribe a")
  Rel(public_consumer, redis, "Suscribe a")
  Rel(results_view, results_svc, "Llama a")
  Rel(results_svc, db, "Lee")
```

### Nivel 3: Diagrama Dinámico - Flujo de Registro Automático

```mermaid
C4Dynamic
  title Flujo - Registro Automático desde Edge

  System_Ext(edge, "Edge/Simulador", "Envía registros")

  Container(web, "Aplicación Web", "Django + DRF")
  ContainerDb(db, "PostgreSQL", "Datos")
  Container(ws, "WebSocket", "Channels + Redis")

  Rel(edge, web, "1. POST /api/registros/ {dorsal, tiempo_ms, confianza_ocr, evidencia}", "HTTPS + Token")
  Rel(web, db, "2. Resuelve dorsal contra Equipo.number de la competencia")
  Rel(web, db, "3. Crea RegistroTiempo con estado = validado o pendiente")
  Rel(web, ws, "4a. Si OCR >= 95%: publica clasificacion_actualizada", "Redis Pub/Sub")
  Rel(web, ws, "4b. Si OCR < 95%: publica registro_pendiente para jueces", "Redis Pub/Sub")
```

### Diagrama de Despliegue

```mermaid
C4Deployment
  title Diagrama de Despliegue - RASC UNL Vision

  Deployment_Node(edge_node, "Dispositivo Edge", "Raspberry Pi 5") {
    Container(edge_app, "rasc-vision-edge", "Python + OpenCV", "Procesamiento de video y OCR")
    ContainerDb(edge_db, "SQLite", "SQLite", "Registros locales pendientes de envío")
  }

  Deployment_Node(dev_node, "Entorno de Desarrollo", "PC/Laptop") {
    Container(sim_app, "Simulador Edge", "Python + Tkinter", "Genera eventos sintéticos")
  }

  Deployment_Node(prod_server, "Servidor de Producción", "Linux / Docker") {
    Deployment_Node(django_ctr, "Contenedor Django", "Docker") {
      Container(web_app, "Django + DRF", "Daphne + Django 6.0", "API REST y templates")
      Container(ws_app, "Channels Worker", "Daphne ASGI", "WebSocket server")
    }
    Deployment_Node(data_ctr, "Contenedores de Datos", "Docker") {
      ContainerDb(pg_db, "PostgreSQL", "PostgreSQL 16", "Datos de aplicación")
      ContainerDb(redis_srv, "Redis", "Redis 7", "Channel layer")
    }
  }

  Deployment_Node(cameras, "Cámaras IP", "RTSP") {
    Container(cam, "Cámara de Meta", "IP Camera", "Stream RTSP")
  }

  Rel(cam, edge_app, "Stream RTSP", "LAN")
  Rel(edge_app, edge_db, "Persiste", "SQLite")
  Rel(edge_app, web_app, "POST /api/registros/", "HTTPS")
  Rel(sim_app, web_app, "POST /api/registros/", "HTTPS")
  Rel(web_app, pg_db, "SQL", "TCP")
  Rel(web_app, redis_srv, "Pub/Sub", "TCP")
  Rel(ws_app, redis_srv, "Pub/Sub", "TCP")
```

## Diagrama UML de Modelos

> Nota: La skill `uml` no se encuentra instalada. Se utilizan diagramas Mermaid `classDiagram` como equivalente.

```mermaid
classDiagram
    class Competencia {
        +BigAutoField id
        +CharField name
        +DateTimeField datetime
        +BooleanField is_active
        +BooleanField is_running
        +DateTimeField started_at
        +DateTimeField finished_at
        +UUIDField token
        +start() Result
        +stop() Result
        +get_status_code() str
    }

    class Equipo {
        +BigAutoField id
        +CharField name
        +PositiveIntegerField number
        +CharField category
        +FK competition
        +FK judge
        +total_time() int
        +average_time() int
        +best_time() int
    }

    class Juez {
        +BigAutoField id
        +CharField username
        +CharField password
        +CharField first_name
        +CharField last_name
        +EmailField email
        +BooleanField is_active
        +set_password() void
        +check_password() bool
    }

    class RegistroTiempo {
        +UUIDField record_id
        +FK team
        +BigIntegerField time
        +CharField origen
        +FloatField confianza_ocr
        +ImageField evidencia_imagen
        +CharField estado
        +PositiveIntegerField dorsal_detectado
        +PositiveIntegerField dorsal_corregido
        +TextField motivo_descalificacion
        +FK validado_por
        +DateTimeField validado_en
    }

    class AuditoriaRegistro {
        +BigAutoField id
        +FK registro_tiempo
        +FK juez
        +CharField accion
        +JSONField valor_anterior
        +JSONField valor_nuevo
        +DateTimeField creado_en
    }

    Competencia "1" --> "*" Equipo : tiene
    Juez "1" --> "*" Equipo : asigna
    Equipo "1" --> "*" RegistroTiempo : registra
    Juez "1" --> "*" AuditoriaRegistro : realiza
    RegistroTiempo "1" --> "*" AuditoriaRegistro : auditado
    Juez "1" --> "0..*" RegistroTiempo : valida
```

## Risks / Trade-offs

- **[Riesgo] Latencia de WebSocket en conexiones inestables** → Mitigación: el panel de validación hace polling vía REST como fallback; el WebSocket es el canal primario pero no único.
- **[Riesgo] Colisión de dorsales** → Mitigación: `Equipo.number` es único dentro de una competencia (`unique_together`). Si el dorsal no coincide con ningún equipo, se rechaza con HTTP 400.
- **[Riesgo] Imágenes grandes en base64** → Mitigación: `evidencia_imagen` se almacena como `ImageField` en disco/S3, no en base64 en la DB. El endpoint acepta upload multipart.
- **[Trade-off] Un solo endpoint Edge** → Simplifica el API pero concentra la lógica de resolución dorsal→equipo en un solo punto. Aceptable dado que la competencia se resuelve del token.
- **[Trade-off] Auditoría en mismo esquema** → Tablas de auditoría crecen con cada acción. Se mitiga con índices por `registro_tiempo_id` y `creado_en` para consultas eficientes, y política de archivado futuro.

## Open Questions

- ¿El simulador debe poder generar eventos con confianza_ocr exactamente en el umbral (95%) para probar casos límite?
El simulador debe permitir poner generar eventos con confianza_ocr personalizada, para poder probar en desarrollo
- ¿La página de resultados debe mostrar solo registros validados o también pendientes? 
Solo reigstros ya validados para el ranking, y pendientes visibles solo para jueces.
