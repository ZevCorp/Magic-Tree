# 🎄 Árbol Encantado - Magic Tree

Experiencia interactiva navideña con detección de voz y captura de video.

## 🚀 Inicio Rápido

### En Raspberry Pi (Recomendado)

Para evitar problemas con Wayland, usa los scripts wrapper que fuerzan X11:

```bash
# Modo de prueba (sin sensor de puerta)
chmod +x run_test.sh
./run_test.sh

# Modo completo (con sensor de puerta)
chmod +x run_main.sh
./run_main.sh
```

### Ejecución Directa (Puede tener problemas en Wayland)

```bash
# Activar entorno virtual
source venv/bin/activate

# Modo de prueba
python test_mode.py

# Modo completo
python main.py
```

## 🔧 Solución de Problemas

### Error: "xdg_wm_base error 4: wrong configure serial"

Este error ocurre cuando el sistema usa Wayland. **Solución**: Usa los scripts `run_test.sh` o `run_main.sh` que fuerzan X11.

### La ventana de feedback no aparece

1. Verifica que los scripts tengan permisos de ejecución: `chmod +x run_*.sh`
2. Usa los scripts wrapper en lugar de ejecutar Python directamente
3. Revisa los logs para ver dónde se bloquea

### La música de fondo no suena

Instala pygame: `pip install pygame`

## 📁 Estructura del Proyecto

- `main.py` - Programa principal con sensor de puerta
- `test_mode.py` - Modo de prueba sin sensor
- `run_main.sh` - Wrapper X11 para main.py
- `run_test.sh` - Wrapper X11 para test_mode.py
- `audio.py` - Gestión de audio y reconocimiento de voz
- `media.py` - Gestión de video y cámara
- `hardware.py` - Control del sensor de puerta
- `messaging.py` - Envío de mensajes WhatsApp
- `config.py` - Configuración del sistema

## 🎯 Flujo de la Experiencia

1. **Espera** - El sistema espera que se abra la puerta (o Enter en modo test)
2. **Video Intro** - Reproducción del video de Santa
3. **Grabación** - Graba al usuario hasta que diga "Feliz Navidad"
4. **Solicitud de Teléfono** - Video pidiendo el número de teléfono
5. **Captura de Teléfono** - Pantalla con fondo navideño que muestra el número dictado
6. **Confirmación** - Usuario dice "Confirmar"
7. **Envío** - Se envía mensaje de WhatsApp con el video

## 📝 Notas Técnicas

- **Sistema de Ventanas**: Los scripts wrapper fuerzan X11 para evitar conflictos con Wayland
- **Detección de Voz**: Usa Vosk para palabras clave y OpenAI Whisper para transcripción
- **Extracción de Números**: GPT-4o interpreta números dictados en varios formatos
- **Display**: OpenCV para UI de feedback, VLC para reproducción de videos
