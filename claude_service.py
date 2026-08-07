"""
Motor de conversación: Claude responde al cliente y usa "tools" (function calling)
para consultar stock/precio real en la base de datos en vez de inventar datos.
"""
import os
import json
import anthropic
from sqlalchemy.orm import Session
from app.models import Producto, Stock

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Sos el asistente de ventas de Phenex Fashion, una tienda de ropa en Argentina.
Atendés por WhatsApp/Instagram/Facebook. Tu tono es cercano, amable, en español rioplatense.

Reglas:
- NUNCA inventes stock, talles o precios. Siempre usá las herramientas (tools) para consultar
  la base de datos real antes de confirmar disponibilidad.
- Si el cliente quiere comprar, armá el pedido con producto/talle/color/cantidad y usá
  la herramienta crear_pedido para generar el link de pago.
- Sé breve, como en una charla de WhatsApp real (no uses párrafos largos).
- Si no tenés el talle o color pedido, ofrecé alternativas disponibles del mismo producto.
"""

TOOLS = [
    {
        "name": "buscar_producto",
        "description": "Busca productos por nombre o categoría y devuelve precio y variantes con stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "termino": {"type": "string", "description": "nombre o categoría a buscar, ej: 'vestido negro'"}
            },
            "required": ["termino"]
        }
    },
    {
        "name": "consultar_stock",
        "description": "Consulta el stock exacto de un producto en un talle y color específico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "producto_id": {"type": "integer"},
                "talle": {"type": "string"},
                "color": {"type": "string"}
            },
            "required": ["producto_id"]
        }
    },
    {
        "name": "crear_pedido",
        "description": "Crea un pedido pendiente de pago y devuelve el link de MercadoPago para enviarle al cliente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "integer"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "producto_id": {"type": "integer"},
                            "talle": {"type": "string"},
                            "color": {"type": "string"},
                            "cantidad": {"type": "integer"}
                        }
                    }
                }
            },
            "required": ["cliente_id", "items"]
        }
    }
]


def _buscar_producto(db: Session, termino: str):
    productos = db.query(Producto).filter(
        Producto.activo == True,
        Producto.nombre.ilike(f"%{termino}%") | Producto.categoria.ilike(f"%{termino}%")
    ).limit(5).all()

    resultado = []
    for p in productos:
        variantes = [
            {"talle": v.talle, "color": v.color, "disponible": v.cantidad_disponible}
            for v in p.variantes if v.cantidad_disponible > 0
        ]
        resultado.append({
            "id": p.id, "nombre": p.nombre, "precio": p.precio,
            "descripcion": p.descripcion, "variantes_con_stock": variantes
        })
    return resultado


def _consultar_stock(db: Session, producto_id: int, talle: str = None, color: str = None):
    q = db.query(Stock).filter(Stock.producto_id == producto_id)
    if talle:
        q = q.filter(Stock.talle == talle)
    if color:
        q = q.filter(Stock.color == color)
    variantes = q.all()
    return [
        {"talle": v.talle, "color": v.color, "disponible": v.cantidad_disponible}
        for v in variantes
    ]


def _crear_pedido(db: Session, cliente_id: int, items: list):
    # Import local para evitar import circular
    from app.pedidos_service import crear_pedido_con_link_pago
    return crear_pedido_con_link_pago(db, cliente_id, items)


def _ejecutar_tool(db: Session, tool_name: str, tool_input: dict):
    if tool_name == "buscar_producto":
        return _buscar_producto(db, tool_input["termino"])
    if tool_name == "consultar_stock":
        return _consultar_stock(db, tool_input["producto_id"], tool_input.get("talle"), tool_input.get("color"))
    if tool_name == "crear_pedido":
        return _crear_pedido(db, tool_input["cliente_id"], tool_input["items"])
    return {"error": "tool no reconocida"}


def generar_descripcion_desde_foto(imagen_base64: str, media_type: str, nombre_producto: str = "") -> str:
    """
    Analiza la foto de una prenda y redacta una descripción de venta lista para publicar.
    Se usa desde el panel admin cuando subís una foto de producto.
    """
    prompt = (
        "Mirá esta foto de una prenda y escribí una descripción de venta para "
        "Instagram/WhatsApp, en español rioplatense, tono cercano y vendedor pero sin "
        "exagerar. Máximo 3 líneas. Mencioná tipo de prenda, color y para qué ocasión "
        "sirve. No inventes materiales que no se vean en la foto."
    )
    if nombre_producto:
        prompt += f" El producto se llama '{nombre_producto}'."

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": imagen_base64}
                },
                {"type": "text", "text": prompt}
            ]
        }]
    )
    return "".join(b.text for b in response.content if b.type == "text")


def responder_mensaje(db: Session, historial: list, mensaje_nuevo: str) -> tuple[str, list]:
    """
    Recibe el historial de la conversación + el mensaje nuevo del cliente.
    Devuelve (respuesta_final_para_el_cliente, historial_actualizado).
    Maneja el loop de tool use de Claude automáticamente.
    """
    messages = historial + [{"role": "user", "content": mensaje_nuevo}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    resultado = _ejecutar_tool(db, block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(resultado, ensure_ascii=False)
                    })
            messages.append({"role": "user", "content": tool_results})
            continue  # vuelve a llamar a Claude con el resultado de la tool

        # Respuesta final de texto
        texto_final = "".join(b.text for b in response.content if b.type == "text")
        messages.append({"role": "assistant", "content": texto_final})
        return texto_final, messages
