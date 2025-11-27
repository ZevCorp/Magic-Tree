# Experiencia del Árbol Encantado (Raspberry Pi 5)

Este proyecto implementa una experiencia interactiva donde un Árbol Encantado (Papá Noel) interactúa con el usuario.

## Funcionalidad
1.  **Detección de Puerta**: Inicia cuando se abre la puerta (Sensor Magnético).
2.  **Intro**: Reproduce un video de bienvenida.
3.  **Grabación**: Graba al usuario hasta que dice "Feliz Navidad".
4.  **Teléfono**: Pide el número de teléfono del usuario.
5.  **Procesamiento**: Transcribe el número usando Whisperflow API.
6.  **Mensaje**: Envía un saludo (simulado/log).

## Requisitos de Hardware
-   Raspberry Pi 5
-   Cámara (USB o CSI)
-   Sensor de puerta (Reed Switch) conectado al GPIO 17 y GND.
-   Altavoces
-   Pantalla

## Instalación

1.  Clona o copia este repositorio en la Raspberry Pi.
2.  Ejecuta el script de instalación:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
3.  **Importante**: Coloca tus archivos de video en la carpeta `assets/`:
    -   `intro.mp4`: Video de Papá Noel hablando.
    -   `ask_phone.mp4`: Video pidiendo el teléfono.
4.  Edita `config.py` y añade tu **API Key de Whisperflow**.

## Ejecución

```bash
source venv/bin/activate
python main.py
```

## Configuración
Puedes ajustar los pines GPIO y otras configuraciones en `config.py`.
