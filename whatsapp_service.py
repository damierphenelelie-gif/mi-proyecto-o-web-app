"""
Integración con WhatsApp Cloud API (Meta).
Requiere: WHATSAPP_TOKEN y WHATSAPP_PHONE_NUMBER_ID (los da Meta for Developers).
"""
import os
import httpx

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"


async def enviar_mensaje_texto(numero_destino: str, texto: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def extraer_mensaje_entrante(payload: dict):
    """
    Parsea el JSON que manda Meta al webhook y devuelve (numero_cliente, texto_mensaje)
    o (None, None) si no es un mensaje de texto de usuario (ej: es un status update).
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]["value"]
        if "messages" not in changes:
            return None, None  # es un status (entregado/leído), no un mensaje nuevo
        mensaje = changes["messages"][0]
        numero = mensaje["from"]
        texto = mensaje.get("text", {}).get("body", "")
        return numero, texto
    except (KeyError, IndexError):
        return None, None
