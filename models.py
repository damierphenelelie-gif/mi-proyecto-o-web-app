"""
Modelos de base de datos - Phenex Fashion
Usa PostgreSQL en producción (Render). Para desarrollo local podés usar SQLite
cambiando la DATABASE_URL en .env
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    categoria = Column(String(100))  # ej: "vestidos", "remeras", "pantalones"
    descripcion = Column(Text)  # generada por IA o manual
    precio = Column(Float, nullable=False)
    fotos = Column(JSON, default=list)  # lista de URLs de imágenes
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    variantes = relationship("Stock", back_populates="producto")


class Stock(Base):
    """Cada combinación de talle/color de un producto tiene su propio stock."""
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    talle = Column(String(10))  # ej: "S", "M", "L", "40", "42"
    color = Column(String(50))
    cantidad_disponible = Column(Integer, default=0)
    cantidad_reservada = Column(Integer, default=0)  # mientras se procesa un pago

    producto = relationship("Producto", back_populates="variantes")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200))
    canal = Column(String(50))  # "whatsapp", "instagram", "facebook", "tiktok"
    identificador_canal = Column(String(200), index=True)  # número de WhatsApp, user ID de IG, etc.
    creado_en = Column(DateTime, default=datetime.utcnow)


class Conversacion(Base):
    """Guarda el historial de mensajes para que Claude mantenga contexto."""
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    canal = Column(String(50))
    historial = Column(JSON, default=list)  # [{"role": "user"/"assistant", "content": "..."}]
    contexto_pedido = Column(JSON, default=dict)  # carrito en construcción
    actualizado_en = Column(DateTime, default=datetime.utcnow)


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    canal_origen = Column(String(50))
    items = Column(JSON)  # [{"producto_id":.., "talle":.., "color":.., "cantidad":.., "precio_unit":..}]
    total = Column(Float)
    estado = Column(String(30), default="pendiente_pago")
    # estados: pendiente_pago, pagado, en_preparacion, enviado, entregado, cancelado
    mercadopago_payment_id = Column(String(100), nullable=True)
    direccion_envio = Column(JSON, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
