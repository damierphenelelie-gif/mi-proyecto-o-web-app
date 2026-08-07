# Phenex Fashion — Backend del Asistente de IA

## Qué incluye este esqueleto

- Base de datos: productos, stock por talle/color, clientes, conversaciones, pedidos.
- Webhook de WhatsApp que recibe mensajes, se los pasa a Claude, y Claude responde
  consultando el stock real (nunca inventa disponibilidad).
- Cierre de venta: Claude puede armar el pedido y generar un link de pago de MercadoPago
  directo en el chat.
- Endpoints básicos para cargar productos (para tu futuro panel admin).

## 1. Instalación local (para probar antes de subir a Render)

```bash
cd phenex-backend
python -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Completá el `.env` con tus claves (ver paso 2 y 3).

Corré el servidor:
```bash
uvicorn app.main:app --reload
```

Se levanta en `http://localhost:8000`. Para desarrollo, va a usar SQLite automáticamente
(no necesitás PostgreSQL instalado en tu compu).

## 2. Conseguir las credenciales de WhatsApp (Meta)

1. Entrá a https://developers.facebook.com y creá una cuenta de desarrollador.
2. Creá una App nueva → tipo "Business".
3. Agregá el producto "WhatsApp" a la app.
4. Meta te da un número de prueba gratis con un `WHATSAPP_PHONE_NUMBER_ID` y un
   `WHATSAPP_TOKEN` temporal (después hay que generar uno permanente).
5. Cuando tengas tu backend corriendo en Render (paso 4), volvé a Meta y configurá el
   webhook con la URL: `https://tu-backend.onrender.com/webhooks/whatsapp` y el mismo
   `WHATSAPP_VERIFY_TOKEN` que pusiste en tu `.env`.
6. Suscribite al campo `messages` del webhook.

## 3. Conseguir el token de MercadoPago

1. Entrá a https://www.mercadopago.com.ar/developers/panel
2. Tus credenciales → Access Token de producción (o de prueba mientras testeás).

## 4. Subir a Render

1. Creá un servicio PostgreSQL en Render (te da la `DATABASE_URL` automáticamente).
2. Creá un "Web Service" nuevo apuntando a este repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Cargá todas las variables de entorno del `.env` en el panel de Render.

## 5. Probar que funciona

Una vez desplegado y el webhook de WhatsApp verificado, escribile al número de prueba
desde tu WhatsApp personal. El mensaje va a llegar al backend, Claude te va a responder
usando el stock que cargues con el endpoint `POST /productos`.

Ejemplo para cargar un producto de prueba (podés usar la doc interactiva en
`https://tu-backend.onrender.com/docs`):

```json
POST /productos
{
  "nombre": "Vestido Bianca",
  "categoria": "vestidos",
  "descripcion": "Vestido negro de gasa, ideal para verano",
  "precio": 45000,
  "fotos": [],
  "variantes": [
    {"talle": "S", "color": "negro", "cantidad_disponible": 3},
    {"talle": "M", "color": "negro", "cantidad_disponible": 5}
  ]
}
```

## Próximos pasos (siguiente fase)

- Panel de administración en React para cargar productos con fotos sin usar `/docs`.
- Completar el webhook de MercadoPago para confirmar pagos y descontar stock definitivo.
- Replicar el mismo patrón de webhook para Instagram y Facebook Messenger (comparten
  la Graph API de Meta, así que reutilizamos casi todo este código).
