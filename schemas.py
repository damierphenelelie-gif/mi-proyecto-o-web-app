from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class StockCreate(BaseModel):
    talle: str
    color: str
    cantidad_disponible: int = 0


class ProductoCreate(BaseModel):
    nombre: str
    categoria: Optional[str] = None
    descripcion: Optional[str] = None
    precio: float
    fotos: Optional[List[str]] = []
    variantes: Optional[List[StockCreate]] = []


class ProductoOut(BaseModel):
    id: int
    nombre: str
    categoria: Optional[str]
    descripcion: Optional[str]
    precio: float
    fotos: List[str]
    activo: bool

    class Config:
        from_attributes = True


class PedidoOut(BaseModel):
    id: int
    items: List[Dict[str, Any]]
    total: float
    estado: str

    class Config:
        from_attributes = True
