# Especificación: Clasificación en Tiempo Real

## ADDED Requirements

### Requirement: Actualización de clasificación vía WebSocket

El sistema SHALL emitir un evento `clasificacion_actualizada` a través del WebSocket público (`CompetenciaPublicConsumer`) cada vez que se cree o valide un `RegistroTiempo`. El evento DEBE contener el ranking completo de equipos ordenado por mejor tiempo.

#### Scenario: Nuevo registro validado actualiza clasificación

- **WHEN** se crea un `RegistroTiempo` con `estado="validado"` (sea automático o por confirmación de juez)
- **THEN** el sistema recalcula el ranking de la competencia
- **THEN** el sistema emite `clasificacion_actualizada` con el ranking completo al grupo `competencia_{id}`

#### Scenario: Registro pendiente no actualiza clasificación pública

- **WHEN** se crea un `RegistroTiempo` con `estado="pendiente"`
- **THEN** el sistema NO emite `clasificacion_actualizada` al WebSocket público
- **THEN** la página de resultados públicos no muestra cambios

### Requirement: Página de resultados con actualización en tiempo real

La página de resultados públicos SHALL suscribirse al WebSocket `CompetenciaPublicConsumer` y actualizar la tabla de clasificación automáticamente cuando reciba el evento `clasificacion_actualizada`.

#### Scenario: Espectador ve resultados actualizarse en vivo

- **WHEN** un espectador tiene abierta la página de resultados de una competencia
- **THEN** la clasificación se actualiza automáticamente sin recargar la página cada vez que se valida un nuevo registro

#### Scenario: Conexión WebSocket caída muestra indicador

- **WHEN** la conexión WebSocket del espectador se interrumpe
- **THEN** la página muestra un indicador visual de "Desconectado" o "Reconectando"
- **THEN** la página reconecta automáticamente y recibe el estado actual

### Requirement: Ranking solo incluye registros validados

El sistema SHALL calcular el ranking de la competencia utilizando únicamente registros con `estado="validado"` o `estado="corregido"`. Los registros `pendiente` y `descalificado` NO DEBEN incluirse en el ranking público.

#### Scenario: Registro pendiente no afecta ranking

- **WHEN** existe un registro con `estado="pendiente"` para un equipo
- **THEN** el ranking público no incluye ese tiempo en el cálculo del equipo

#### Scenario: Registro descalificado no afecta ranking

- **WHEN** un equipo tiene un registro con `estado="descalificado"`
- **THEN** ese registro se excluye del cálculo de tiempos del equipo en el ranking

#### Scenario: Registro corregido sí afecta ranking

- **WHEN** un registro tiene `estado="corregido"` con un `dorsal_corregido` válido
- **THEN** el tiempo se asigna al equipo resuelto por el dorsal corregido y se incluye en el ranking

### Requirement: Formato del evento de clasificación

El evento `clasificacion_actualizada` emitido por WebSocket SHALL contener la lista de equipos con: posición, `equipo_id`, `equipo_nombre`, `equipo_dorsal`, `mejor_tiempo`, `tiempo_total` y `num_registros`.

#### Scenario: Evento contiene datos completos del ranking

- **WHEN** el sistema emite `clasificacion_actualizada`
- **THEN** el payload incluye un array `ranking` con objetos que contienen `posicion`, `equipo_id`, `equipo_nombre`, `equipo_dorsal`, `mejor_tiempo`, `tiempo_total` y `num_registros`
- **THEN** el ranking está ordenado por `mejor_tiempo` ascendente

### Requirement: Envío de clasificación al conectar

El sistema SHALL enviar la clasificación actual completa cuando un cliente se conecta por primera vez al WebSocket público, sin necesidad de esperar un nuevo evento.

#### Scenario: Cliente recibe clasificación inicial al conectar

- **WHEN** un espectador abre la página de resultados y se conecta al WebSocket
- **THEN** el sistema envía inmediatamente la clasificación actual como evento `conexion_establecida` con el ranking
