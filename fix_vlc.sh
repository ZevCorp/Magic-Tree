#!/bin/bash
echo "==================================================="
echo "   REPARADOR DE SISTEMA VIDEO (MAGIC TREE)"
echo "==================================================="
echo ""
echo "[1/3] Borrando caché de configuración de VLC..."
rm -rf ~/.config/vlc
rm -rf ~/.cache/vlc
echo "      Caché borrada."
echo ""

echo "[2/3] Buscando plugin conflictivo V4L2..."
# En RPi OS (Debian), suele estar en /usr/lib/aarch64-linux-gnu/vlc/plugins/codec/
PLUGIN_PATH=$(find /usr/lib -name "libv4l2_plugin.so" 2>/dev/null | head -n 1)

if [ -f "$PLUGIN_PATH" ]; then
    echo "      Encontrado: $PLUGIN_PATH"
    echo "      Desactivando plugin para forzar modo seguro (Software Decoding)..."
    sudo mv "$PLUGIN_PATH" "${PLUGIN_PATH}.bak"
    if [ $? -eq 0 ]; then
        echo "      EXITO: Plugin desactivado."
    else
        echo "      ERROR: No se pudo desactivar (¿permisos?)."
    fi
else
    echo "      AVISO: No se encontró el plugin libv4l2_plugin.so (¿Ya estaba desactivado?)"
fi

echo ""
echo "[3/3] Verificando..."
if [ -f "${PLUGIN_PATH}.bak" ]; then
    echo "      Estado: SEGURO (Plugin .bak existe)"
else
    echo "      Estado: INDETERMINADO"
fi

echo ""
echo "==================================================="
echo "   LISTO. PRUEBA EJECUTAR LA EXPERIENCIA AHORA"
echo "==================================================="
read -p "Presiona Enter para salir..."
