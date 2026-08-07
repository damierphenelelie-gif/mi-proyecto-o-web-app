import os
import mercadopago
from sqlalchemy.orm import Session
from app.models import Pedido, Stock, Producto

sdk = mercadopago.SDK(os.getenv("MERCADOPAGO_ACCESS_TOKEN"))


def crear_pedido_con_link_pago(db: Session, cliente_id: int, items: list) -> dict:
    """
    items: [{"producto_id":1, "talle":"M", "color":"negro", "cantidad":1}, ...]
    Verifica stock real, reserva la cantidad, calcula el total y genera el link de pago.
    """
    detalle_items_mp = []
    items_pedido = []
    total = 0.0

    for item in items:
        stock = db.query(Stock).filter(
            Stock.producto_id == item["producto_id"],
            Stock.talle == item.get("talle"),
            Stock.color == item.get("color")
        ).first()

        if not stock or stock.cantidad_disponible < item["cantidad"]:
            return {"error": f"Sin stock suficiente para el producto {item['producto_id']} "
                              f"talle {item.get('talle')} color {item.get('color')}"}

        producto = db.query(Producto).get(item["producto_id"])

        # Reservamos el stock mientras se procesa el pago
        stock.cantidad_disponible -= item["cantidad"]
        stock.cantidad_reservada += item["cantidad"]

        subtotal = producto.precio * item["cantidad"]
        total += subtotal

        items_pedido.append({**item, "precio_unit": producto.precio})
        detalle_items_mp.append({
            "title": f"{producto.nombre} ({item.get('talle')}/{item.get('color')})",
            "quantity": item["cantidad"],
            "unit_price": producto.precio,
            "currency_id": "ARS"
        })

    pedido = Pedido(
        cliente_id=cliente_id,
        canal_origen="whatsapp",
        items=items_pedido,
        total=total,
        estado="pendiente_pago"
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    preference_data = {
        "items": detalle_items_mp,
        "external_reference": str(pedido.id),
        "back_urls": {
            "success": os.getenv("MP_SUCCESS_URL", "https://phenexfashion.com/gracias"),
        },
        "notification_url": os.getenv("MP_WEBHOOK_URL"),  # ver endpoint /webhooks/mercadopago
    }
    preference = sdk.preference().create(preference_data)
    link_pago = preference["response"]["init_point"]

    return {
        "pedido_id": pedido.id,
        "total": total,
        "link_pago": link_pago
    }
