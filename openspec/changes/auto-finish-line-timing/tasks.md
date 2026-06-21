# Tareas: Cronometraje Automático con Visión por Computadora

## 1. Backend - Modelos y Base de Datos

- [ ] 1.1 Extender `RegistroTiempo` con nuevos campos: `origen`, `confianza_ocr`, `evidencia_imagen`, `estado`, `dorsal_detectado`, `dorsal_corregido`, `motivo_descalificacion`, `validado_por`, `validado_en`
- [ ] 1.2 Agregar campo `token` (UUIDField, único, autogenerado) al modelo `Competencia`
- [ ] 1.3 Crear modelo `AuditoriaRegistro` con campos: `registro_tiempo` (FK), `juez` (FK), `accion`, `valor_anterior` (JSON), `valor_nuevo` (JSON), `creado_en`
- [ ] 1.4 Generar y aplicar migraciones (`makemigrations` + `migrate`)
- [ ] 1.5 Actualizar el `__init__.py` de modelos para exportar `AuditoriaRegistro`

## 2. Backend - Autenticación y Tokens

- [ ] 2.1 Implementar `EdgeTokenAuth` (DRF Authentication) que valide el header `Authorization: Token <uuid>` contra `Competencia.token` y `is_active`
- [ ] 2.2 Implementar vista de registro público de jueces (`register/`) vinculando `User` de Django con perfil `Juez`
- [ ] 2.3 Implementar vista de login/logout para jueces usando el sistema de autenticación de Django
- [ ] 2.4 Configurar permisos: `IsJudgeAuthenticated` para panel de validación
- [ ] 2.5 Modificar el admin de `Competencia` para mostrar el campo `token` como solo lectura en lista y detalle

## 3. Backend - API de Recepción de Registros (Edge)

- [ ] 3.1 Crear `EdgeRegistroSerializer` validando campos: `dorsal`, `tiempo_ms`, `confianza_ocr`, `evidencia_imagen` (opcional)
- [ ] 3.2 Crear vista `EdgeRegistroView` (`POST /api/registros/`) con autenticación `EdgeTokenAuth`
- [ ] 3.3 Implementar `RegistroService.procesar_registro_edge()`: resolver dorsal contra `Equipo.number` de la competencia del token
- [ ] 3.4 Implementar lógica de decisión: si `confianza_ocr >= 95` → `origen="automatico"`, `estado="validado"`; si `< 95` → `origen="manual"`, `estado="pendiente"`
- [ ] 3.5 Manejar errores: dorsal no encontrado (400), token inválido/inactivo (400), datos inválidos (400)
- [ ] 3.6 Almacenar `evidencia_imagen` como `ImageField` cuando sea enviada (JPEG decodificado de base64)
- [ ] 3.7 Registrar URL del endpoint en `app/config/urls.py`

## 4. Backend - Panel de Validación de Jueces

- [ ] 4.1 Crear `ValidacionService` con métodos: `confirmar_registro()`, `corregir_dorsal()`, `descalificar_participante()`
- [ ] 4.2 Crear vista `ValidacionPendientesView` (`GET /api/validacion/pendientes/`) listando registros con `estado="pendiente"` de la competencia activa
- [ ] 4.3 Crear vista `ConfirmarRegistroView` (`POST /api/validacion/{id}/confirmar/`) que cambia estado a `"validado"`
- [ ] 4.4 Crear vista `CorregirDorsalView` (`POST /api/validacion/{id}/corregir/`) que asigna `dorsal_corregido` y cambia estado a `"corregido"`
- [ ] 4.5 Crear vista `DescalificarParticipanteView` (`POST /api/validacion/{id}/descalificar/`) con validación de `motivo_descalificacion` obligatorio
- [ ] 4.6 Crear template Django `validacion/panel.html` con lista de pendientes, visor de imagen y formularios de acción
- [ ] 4.7 Crear template `jueces/register.html` para registro público
- [ ] 4.8 Crear template `jueces/login.html` para inicio de sesión
- [ ] 4.9 Configurar rutas de templates en `app/config/ui_urls.py`

## 5. Backend - WebSocket y Clasificación en Tiempo Real

- [ ] 5.1 Extender `JuezConsumer` para unirse al grupo `validacion_{competencia_id}` y recibir eventos `registro_pendiente`
- [ ] 5.2 Implementar envío de notificación `registro_pendiente` desde `RegistroService` cuando se cree un registro con `estado="pendiente"`
- [ ] 5.3 Modificar `ResultsService.obtener_ranking_competencia()` para filtrar solo registros con `estado="validado"` o `"corregido"`
- [ ] 5.4 Implementar emisión de evento `clasificacion_actualizada` con ranking completo al grupo `competencia_{id}` tras cada validación
- [ ] 5.5 Extender `CompetenciaPublicConsumer` para enviar clasificación inicial al conectar (evento `conexion_establecida`)
- [ ] 5.6 Actualizar template de resultados públicos para suscribirse a WebSocket y renderizar ranking en tiempo real

## 6. Backend - Auditoría

- [ ] 6.1 Implementar `AuditoriaService.registrar_accion()` que crea `AuditoriaRegistro` con `valor_anterior` y `valor_nuevo` en JSON
- [ ] 6.2 Integrar `AuditoriaService` en `ValidacionService` para cada acción (confirmar, corregir, descalificar)
- [ ] 6.3 Crear vista `AuditoriaListView` (`GET /api/auditoria/`) para consultar historial de auditoría (admin/jueces)

## 7. Backend - Pruebas Unitarias y de Integración

- [ ] 7.1 Pruebas del modelo `RegistroTiempo`: creación con nuevos campos, restricciones de estado/motivo
- [ ] 7.2 Pruebas del modelo `AuditoriaRegistro`: inmutabilidad, relaciones FK
- [ ] 7.3 Pruebas de `EdgeTokenAuth`: token válido, inválido, competencia inactiva, sin token
- [ ] 7.4 Pruebas de `POST /api/registros/`: auto-validación (OCR >= 95%), pendiente (OCR < 95%), dorsal no encontrado, token inválido
- [ ] 7.5 Pruebas del panel de validación: confirmar, corregir dorsal, descalificar (con/sin motivo)
- [ ] 7.6 Pruebas de WebSocket: notificación `registro_pendiente`, emisión `clasificacion_actualizada`
- [ ] 7.7 Pruebas de integración: flujo completo Edge → registro → validación → clasificación

## 8. Backend - Documentación y Configuración

- [ ] 8.1 Documentar decisión de arquitectura (ADR): token de competencia como API Key
- [ ] 8.2 Documentar ADR: extensión de RegistroTiempo vs modelo separado
- [ ] 8.3 Documentar API REST con Swagger/OpenAPI (actualizar `drf-spectacular`)
- [ ] 8.4 Actualizar `README.md` con instrucciones de setup, variables de entorno y flujo de desarrollo
- [ ] 8.5 Agregar configuración en `.env.example` para `EDGE_TOKEN` y variables relacionadas

## 9. Edge - Simulador (Proyecto Externo)

> **Dependencia**: Requiere que los módulos 1-3 del Backend estén completos y el endpoint `POST /api/registros/` funcional.

- [ ] 9.1 Inicializar proyecto `simulador-edge` (repositorio independiente, Python + Tkinter)
- [ ] 9.2 Implementar cliente HTTP con autenticación `EDGE_TOKEN` y reintento cada 10 segundos en caso de error
- [ ] 9.3 Implementar persistencia local en SQLite de registros pendientes de envío
- [ ] 9.4 Implementar generación de eventos sintéticos: dorsal aleatorio en rango configurable, tiempo incremental, confianza OCR aleatoria
- [ ] 9.5 Implementar interfaz gráfica Tkinter: indicador de conexión, nombre de competencia, modo automático/manual, formulario de envío manual, log en vivo
- [ ] 9.6 Pruebas unitarias del simulador

## 10. Edge - rasc-vision-edge (Proyecto Externo)

> **Dependencia**: Requiere hardware (Raspberry Pi) con cámaras IP RTSP. Mientras no esté disponible, se usa el Simulador.

- [ ] 10.1 Inicializar proyecto `rasc-vision-edge` (repositorio independiente, Python)
- [ ] 10.2 Implementar captura de video RTSP desde cámaras IP usando OpenCV
- [ ] 10.3 Implementar detección de cruce de meta (visión por computadora)
- [ ] 10.4 Implementar OCR de dorsales con EasyOCR
- [ ] 10.5 Implementar cliente HTTP para enviar registros al backend con `EDGE_TOKEN` e imagen JPEG en base64
- [ ] 10.6 Implementar persistencia local en SQLite con reintento de envío
- [ ] 10.7 Pruebas unitarias del procesamiento de visión y OCR
