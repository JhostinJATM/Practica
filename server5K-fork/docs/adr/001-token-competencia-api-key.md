# ADR-001: Token de Competencia como API Key para Autenticación Edge

**Fecha:** 2026-06-21
**Estado:** Aceptado
**Decisión:** Autenticar dispositivos Edge/simulador mediante token UUID (API Key) en lugar de JWT.

## Contexto

Los dispositivos Edge (Raspberry Pi) y el Simulador deben autenticarse para enviar registros de tiempo al backend. Se evaluaron dos opciones: JWT (mismo esquema que jueces) y API Key (token UUID de competencia).

## Opciones Consideradas

1. **JWT para Edge** - Usar `djangorestframework-simplejwt` igual que los jueces, con endpoints `/api/login/` y `/api/token/refresh/`.
2. **API Key (Token UUID)** - Header `Authorization: Token <uuid>`, validado contra `Competencia.token`.

## Decisión

Se eligió **API Key (Token UUID)** por las siguientes razones:

- **Simplicidad en el Edge**: Dispositivos con recursos limitados no necesitan manejar refresh tokens ni sesiones. Un solo UUID basta.
- **Acoplamiento semántico**: El token identifica directamente la competencia. No hay lookup adicional de "a qué competencia pertenece este Edge".
- **Generación automática**: El token se genera como UUID v4 al crear la competencia, visible en el panel de administración.
- **Revocación simple**: Desactivar la competencia (`is_active=False`) invalida inmediatamente el token.

## Consecuencias

- Se implementó `EdgeTokenAuth` en `app/auth/authentication.py`.
- El endpoint `POST /api/registros/` usa exclusivamente autenticación por token.
- El header requerido es `Authorization: Token <uuid>`.
- Si el token no existe o la competencia no está activa, se responde HTTP 401.
