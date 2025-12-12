#!/bin/bash
# Script para iniciar el backend de Mykonos en puerto 8080

echo "🚀 Iniciando Mykonos Backend en puerto 8080..."

# Verificar si existe el archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Advertencia: No se encontró archivo .env"
    echo "📝 Copiando .env.example a .env..."
    cp .env.example .env
    echo "✅ Archivo .env creado. Por favor, configura tus variables de entorno."
fi

# Activar entorno virtual
if [ -d "venv" ]; then
    echo "🔧 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "⚠️  No se encontró entorno virtual. Creando..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Instalando dependencias..."
    pip install -r requirements.txt
fi

# Iniciar el servidor con uvicorn en puerto 8080
echo "🌐 Iniciando servidor en 0.0.0.0:8080..."
uvicorn main:app --host 0.0.0.0 --port 8080 --reload


