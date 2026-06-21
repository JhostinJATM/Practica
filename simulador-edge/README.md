# Simulador Edge - RASC UNL Vision

Simulador para desarrollo sin dispositivo Edge ni cámaras IP reales.

Genera eventos sintéticos de cruce de meta y los envía al backend `server5k-fork`.

## Requisitos

- Python 3.10+
- requests
- tkinter (incluido en Python estándar)

```bash
pip install requests
```

## Configuración

```bash
cp .env.example .env
# Editar .env con:
#   BACKEND_URL=http://localhost:8000
#   EDGE_TOKEN=<uuid-de-la-competencia>
```

## Ejecución

```bash
python main.py
```

## Interfaz

- **Indicador de conexión**: Conectado (verde) / Desconectado (rojo)
- **Nombre de la competencia**: Obtenido del backend
- **Modo Automático**: Envío periódico configurable (dorsales + intervalo)
- **Modo Manual**: Formulario para envío individual (dorsal, tiempo, confianza OCR)
- **Log en vivo**: Timestamp + resultado de cada envío

## Pruebas

```bash
python -m pytest tests/ -v
```
