# Solución de Problemas - GPIO

## Error: "BadPinFactory: Unable to load any default pin factory!"

Este error ocurre cuando gpiozero no puede acceder al hardware GPIO. Hay varias soluciones:

### Solución 1: Instalar lgpio (Recomendado para Raspberry Pi 5)
```bash
sudo apt-get install python3-lgpio
pip install lgpio
```

### Solución 2: Añadir usuario al grupo GPIO
```bash
sudo usermod -a -G gpio $USER
sudo reboot
```

### Solución 3: Ejecutar con sudo (No recomendado)
```bash
sudo venv/bin/python main.py
```

### Solución 4: Modo de Prueba (Sin Hardware)
Si solo quieres probar el software sin el hardware conectado:
```bash
python test_mode.py
```

## Otros Problemas Comunes

### Error de ALSA (Audio)
Los mensajes de ALSA son advertencias normales en Raspberry Pi. No afectan el funcionamiento.

### Error de Whisperflow API
```
ERROR:root:Exception calling Whisperflow: ... Failed to resolve 'api.whisperflow.io'
```

**Solución:**
1. Verifica tu conexión a internet
2. Verifica que la URL de la API en `config.py` sea correcta
3. Verifica que tu API key sea válida

### Video no se reproduce
**Solución:**
1. Asegúrate de que los archivos `intro.mp4` y `ask_phone.mp4` estén en la carpeta `assets/`
2. Verifica que VLC esté instalado: `sudo apt-get install vlc libvlc-dev`

## Verificar Instalación

Para verificar que todo está instalado correctamente:
```bash
python -c "import cv2, vlc, vosk, pyaudio, gpiozero; print('Todo OK')"
```

### Error de Puppeteer / Chrome (SingletonLock)
Si ves un error como `Failed to create .../SingletonLock: File exists`, significa que una sesión anterior de Chrome quedó abierta.

**Solución:**
1. Detén los procesos de Chrome:
   ```bash
   pkill -f chromium
   ```
2. Elimina el archivo de bloqueo:
   ```bash
   rm -rf .wwebjs_auth/session/SingletonLock
   ```
3. Si el problema persiste, borra toda la carpeta de sesión (requerirá escanear QR de nuevo):
   ```bash
   rm -rf .wwebjs_auth
   ```

### Error: "No LID for user" o "Evaluation failed"
Este error ocurre cuando el número de teléfono no tiene el formato correcto para WhatsApp o no está registrado.

**Solución:**
El sistema ahora intenta corregir automáticamente el formato (probando con y sin el código de país '1' para México).
Si el error persiste:
1. Verifica que el número sea válido y tenga WhatsApp.
2. Intenta borrar la sesión (`rm -rf .wwebjs_auth`) y volver a vincular.
