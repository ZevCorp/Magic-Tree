#!/bin/bash
# Script simplificado para iniciar la Experiencia del Árbol Encantado
# Coloca este archivo (o un enlace a él) en el escritorio.

# 1. Navegar al directorio del proyecto (asumiendo que está donde reside este script)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================="
echo "   INICIANDO ARBOL ENCANTADO (TEST MODE)  "
echo "=========================================="
echo "Directorio: $DIR"

# 2. Activar Entorno Virtual
if [ -d "venv" ]; then
    echo "Activando entorno virtual..."
    source venv/bin/activate
else
    echo "ERROR: No se encontró la carpeta 'venv'."
    echo "Por favor ejecuta ./setup.sh primero."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# 3. Ejecutar run_test.sh
if [ -f "run_test.sh" ]; then
    chmod +x run_test.sh
    ./run_test.sh
else
    echo "ERROR: No se encontró run_test.sh"
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo "=========================================="
echo "   EXPERIENCIA FINALIZADA                 "
echo "=========================================="
read -p "Presiona Enter para cerrar esta ventana..."
