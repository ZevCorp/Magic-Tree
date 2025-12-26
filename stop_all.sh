#!/bin/bash
# ============================================
# STOP ALL - Magic Tree
# Detiene run_test.sh y el servidor de WhatsApp
# ============================================

echo "🛑 Deteniendo Magic Tree..."
echo "================================"

# Detener procesos de node server.js (WhatsApp)
if pgrep -f "node server.js" > /dev/null; then
    echo "⏹️  Deteniendo servidor de WhatsApp..."
    pkill -f "node server.js"
    sleep 1
    # Forzar si aún existe
    if pgrep -f "node server.js" > /dev/null; then
        pkill -9 -f "node server.js"
    fi
    echo "   ✅ Servidor de WhatsApp detenido"
else
    echo "   ℹ️  Servidor de WhatsApp no estaba corriendo"
fi

# Detener run_test.sh
if pgrep -f "run_test.sh" > /dev/null; then
    echo "⏹️  Deteniendo run_test.sh..."
    pkill -f "run_test.sh"
    echo "   ✅ run_test.sh detenido"
else
    echo "   ℹ️  run_test.sh no estaba corriendo"
fi

# Detener test_mode.py si está corriendo
if pgrep -f "test_mode.py" > /dev/null; then
    echo "⏹️  Deteniendo test_mode.py..."
    pkill -f "test_mode.py"
    echo "   ✅ test_mode.py detenido"
else
    echo "   ℹ️  test_mode.py no estaba corriendo"
fi

# Detener cualquier proceso de chromium relacionado con whatsapp-web.js
if pgrep -f "chromium.*whatsapp" > /dev/null 2>&1; then
    echo "⏹️  Deteniendo Chromium (WhatsApp)..."
    pkill -f "chromium.*whatsapp"
    echo "   ✅ Chromium detenido"
fi

# Liberar puerto 3000 por si acaso
if lsof -i :3000 > /dev/null 2>&1; then
    echo "⏹️  Liberando puerto 3000..."
    kill -9 $(lsof -t -i :3000) 2>/dev/null
    echo "   ✅ Puerto 3000 liberado"
fi

echo "================================"
echo "✅ Magic Tree detenido completamente"
echo ""
echo "Ahora puedes ejecutar manualmente:"
echo "  cd ~/Desktop/Magic-Tree/messaging && node server.js"
echo ""

# Mantener ventana abierta para ver el resultado
read -p "Presiona Enter para cerrar..."
