#!/bin/bash
# =============================================================================
# fix_audio.sh - Script de diagnóstico y reparación de audio para Magic Tree
# 
# Úsalo cuando aparezcan errores de ALSA/dmix intermitentes
# Ejecuta: ./fix_audio.sh
# =============================================================================

echo "🔧 Magic Tree - Diagnóstico de Audio"
echo "====================================="
echo ""

# 1. Verificar estado de PipeWire
echo "1️⃣  Verificando PipeWire..."
if systemctl --user is-active --quiet pipewire; then
    echo "   ✅ PipeWire está corriendo"
else
    echo "   ❌ PipeWire NO está corriendo"
    echo "   🔄 Reiniciando PipeWire..."
    systemctl --user restart pipewire pipewire-pulse
    sleep 2
    if systemctl --user is-active --quiet pipewire; then
        echo "   ✅ PipeWire reiniciado correctamente"
    else
        echo "   ❌ No se pudo reiniciar PipeWire"
    fi
fi
echo ""

# 2. Verificar estado de PipeWire-Pulse
echo "2️⃣  Verificando PipeWire-Pulse..."
if systemctl --user is-active --quiet pipewire-pulse; then
    echo "   ✅ PipeWire-Pulse está corriendo"
else
    echo "   ❌ PipeWire-Pulse NO está corriendo"
    echo "   🔄 Reiniciando PipeWire-Pulse..."
    systemctl --user restart pipewire-pulse
    sleep 2
fi
echo ""

# 3. Verificar dispositivo de audio activo
echo "3️⃣  Dispositivo de salida activo:"
SINK=$(pactl get-default-sink 2>/dev/null)
if [ -n "$SINK" ]; then
    echo "   🔊 $SINK"
else
    echo "   ⚠️  No hay dispositivo de salida configurado"
fi
echo ""

# 4. Verificar ~/.asoundrc
echo "4️⃣  Verificando configuración ALSA..."
if [ -f ~/.asoundrc ]; then
    if grep -q "type pipewire" ~/.asoundrc; then
        echo "   ✅ ~/.asoundrc configurado correctamente para PipeWire"
    else
        echo "   ⚠️  ~/.asoundrc existe pero no está optimizado"
        echo "   💡 Considera ejecutar el bloque de creación de .asoundrc"
    fi
else
    echo "   ⚠️  ~/.asoundrc no existe"
    echo ""
    echo "   🔄 Creando ~/.asoundrc optimizado..."
    cat > ~/.asoundrc << 'ASOUND'
pcm.!default {
    type pipewire
    playback_node "-1"
    capture_node  "-1"
}
ctl.!default {
    type pipewire
}
pcm.dmixer {
    type pipewire
}
pcm.pulse {
    type pipewire
}
pcm.front cards.pcm.default
pcm.rear cards.pcm.default
pcm.center_lfe cards.pcm.default
pcm.side cards.pcm.default
pcm.surround21 cards.pcm.default
pcm.surround40 cards.pcm.default
pcm.surround41 cards.pcm.default
pcm.surround50 cards.pcm.default
pcm.surround51 cards.pcm.default
pcm.surround71 cards.pcm.default
pcm.iec958 cards.pcm.default
pcm.spdif cards.pcm.default
pcm.modem cards.pcm.default
pcm.phoneline cards.pcm.default
ASOUND
    echo "   ✅ ~/.asoundrc creado"
fi
echo ""

# 5. Matar procesos zombie de audio
echo "5️⃣  Limpiando procesos de audio huérfanos..."
pkill -9 -f "pulseaudio" 2>/dev/null && echo "   🧹 Proceso de PulseAudio terminado" || echo "   ✅ No hay procesos PulseAudio huérfanos"
echo ""

# 6. Reset de WirePlumber (gestor de sesiones de PipeWire)
echo "6️⃣  Reiniciando WirePlumber..."
if systemctl --user is-active --quiet wireplumber; then
    systemctl --user restart wireplumber
    echo "   ✅ WirePlumber reiniciado"
else
    echo "   ℹ️  WirePlumber no está como servicio systemd"
fi
echo ""

# 7. Test de audio rápido
echo "7️⃣  Probando audio..."
if command -v speaker-test &> /dev/null; then
    echo "   🔊 Reproduciendo tono de prueba por 1 segundo..."
    timeout 1 speaker-test -t sine -f 440 -l 1 2>/dev/null >/dev/null && echo "   ✅ Audio funciona" || echo "   ⚠️  El test de audio falló"
else
    echo "   ℹ️  speaker-test no disponible"
fi
echo ""

echo "====================================="
echo "🎉 Diagnóstico completado"
echo ""
echo "Si el problema persiste, intenta:"
echo "  1. Desconectar y reconectar Bluetooth/HDMI"
echo "  2. Ejecutar: systemctl --user restart pipewire pipewire-pulse wireplumber"
echo "  3. Reiniciar el sistema"
echo ""
