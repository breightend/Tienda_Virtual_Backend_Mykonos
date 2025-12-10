# Configuración de FastAPI-Mail

## Resumen

Se migró el sistema de emails de EmailJS a FastAPI-Mail para tener control completo desde el backend.

---

## Ventajas de FastAPI-Mail

✅ **Control total**: Todos los emails se envían desde el backend
✅ **Sin límites**: No dependes de servicios externos con límites
✅ **Múltiples propósitos**: Un solo sistema para todos los tipos de email
✅ **Personalización**: Templates HTML completamente personalizables
✅ **Seguridad**: Credenciales en el backend, no expuestas en el frontend

---

## Configuración

### 1. Instalar Dependencias

```bash
cd backend_tienda_virtual
pip install -r requirements.txt
```

### 2. Configurar Gmail (Recomendado)

#### Opción A: Contraseña de Aplicación (Más Seguro)

1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Seguridad → Verificación en dos pasos (actívala si no la tienes)
3. Seguridad → Contraseñas de aplicaciones
4. Selecciona "Correo" y "Otro dispositivo personalizado"
5. Nombre: "Mykonos Backend"
6. Copia la contraseña generada (16 caracteres)

#### Opción B: Permitir Apps Menos Seguras (No Recomendado)

Solo si no puedes usar contraseñas de aplicación:
1. Ve a https://myaccount.google.com/lesssecureapps
2. Activa "Permitir aplicaciones menos seguras"

### 3. Crear Archivo .env

Crea un archivo `.env` en `backend_tienda_virtual/`:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mykonos_db
DB_USER=postgres
DB_PASSWORD=tu_password

# Email Configuration
MAIL_USERNAME=mykonosboutique733@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion_aqui
MAIL_FROM=mykonosboutique733@gmail.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com

# Application Settings
FRONTEND_URL=http://localhost:5173
```

**IMPORTANTE**: Reemplaza `tu_contraseña_de_aplicacion_aqui` con la contraseña de 16 caracteres que generaste.

### 4. Verificar Configuración

Inicia el backend y verifica que no haya errores:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

---

## Tipos de Emails Implementados

### 1. Verificación de Email (Registro)

**Cuándo se envía**: Automáticamente al registrarse un usuario

**Función**: `send_verification_email()`

**Contenido**:
- Saludo personalizado
- Botón de verificación
- Link alternativo
- Diseño HTML profesional

### 2. Formulario de Contacto

**Cuándo se envía**: Cuando un usuario envía el formulario de contacto

**Función**: `send_contact_email()`

**Contenido**:
- Datos del contacto (nombre, email, teléfono)
- Mensaje del usuario
- Reply-to configurado para responder directamente

### 3. Restablecimiento de Contraseña

**Cuándo se envía**: Cuando un usuario solicita restablecer su contraseña

**Función**: `send_password_reset_email()`

**Contenido**:
- Link de restablecimiento
- Advertencia de expiración (1 hora)
- Diseño con color de alerta

### 4. Actualización de Pedido

**Cuándo se envía**: Cuando cambia el estado de un pedido

**Función**: `send_order_status_email()`

**Contenido**:
- Número de pedido
- Nuevo estado
- Descripción del cambio
- Link al seguimiento

---

## Uso en el Código

### Enviar Email de Verificación

```python
from utils.email import send_verification_email

await send_verification_email(
    email="usuario@example.com",
    username="usuario123",
    verification_token="abc-123-def"
)
```

### Enviar Email de Contacto

```python
from utils.email import send_contact_email

await send_contact_email(
    name="Juan Pérez",
    email="juan@example.com",
    phone="+54 9 11 1234-5678",
    message_text="Consulta sobre productos..."
)
```

### Enviar Actualización de Pedido

```python
from utils.email import send_order_status_email

await send_order_status_email(
    email="usuario@example.com",
    username="usuario123",
    order_id=456,
    status="Despachado",
    description="Tu pedido ha sido entregado al correo"
)
```

---

## Personalizar Templates

Los templates HTML están en `utils/email.py`. Puedes modificarlos directamente:

```python
html_content = f"""
<html>
    <body style="font-family: Arial, sans-serif;">
        <!-- Tu HTML personalizado aquí -->
    </body>
</html>
"""
```

**Consejos**:
- Usa estilos inline (no CSS externo)
- Mantén el diseño simple
- Prueba en diferentes clientes de email
- Usa colores de tu marca

---

## Solución de Problemas

### Error: "Authentication failed"

**Causa**: Contraseña incorrecta o no es contraseña de aplicación

**Solución**:
1. Verifica que usaste la contraseña de aplicación (16 caracteres)
2. No uses tu contraseña normal de Gmail
3. Asegúrate de tener verificación en dos pasos activada

### Error: "Connection refused"

**Causa**: Puerto o servidor SMTP incorrectos

**Solución**:
```env
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
```

### Emails no llegan

**Posibles causas**:
1. Revisa la carpeta de spam
2. Verifica que `MAIL_FROM` sea el mismo que `MAIL_USERNAME`
3. Chequea los logs del backend para errores

### Error: "SSL/TLS"

**Solución**: Verifica la configuración:
```python
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

---

## Otros Proveedores de Email

### Outlook/Hotmail

```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
```

### Yahoo

```env
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
```

### Servicio SMTP Personalizado

```env
MAIL_SERVER=smtp.tudominio.com
MAIL_PORT=587
MAIL_USERNAME=noreply@tudominio.com
MAIL_PASSWORD=tu_password
```

---

## Testing

### Probar Email de Verificación

1. Registra un nuevo usuario
2. Verifica que llegue el email
3. Haz clic en el link de verificación
4. Confirma que la cuenta se active

### Probar Email de Contacto

1. Ve a la página de contacto
2. Llena el formulario
3. Envía el mensaje
4. Verifica que llegue a mykonosboutique733@gmail.com

---

## Migración Completada

### ✅ Removido del Frontend

- ❌ EmailJS dependency
- ❌ Variables de entorno de EmailJS
- ❌ Código de EmailJS en componentes

### ✅ Agregado al Backend

- ✅ FastAPI-Mail dependency
- ✅ Módulo `utils/email.py`
- ✅ Endpoint `/contact/submit`
- ✅ Envío automático en registro
- ✅ Configuración en `.env`

---

## Próximos Pasos

1. **Configurar .env** con tus credenciales de Gmail
2. **Instalar dependencias**: `pip install -r requirements.txt`
3. **Reiniciar backend**: `uvicorn main:app --reload`
4. **Probar registro** de usuario
5. **Probar formulario** de contacto

---

## Notas Importantes

> [!IMPORTANT]
> **Seguridad**: Nunca subas el archivo `.env` a Git. Ya está en `.gitignore`.

> [!WARNING]
> **Contraseña de Aplicación**: Usa SIEMPRE contraseña de aplicación, no tu contraseña normal de Gmail.

> [!TIP]
> **Producción**: En producción, considera usar un servicio SMTP dedicado como SendGrid, Mailgun o Amazon SES para mejor deliverability.
