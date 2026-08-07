import os
import uuid
from fastapi import FastAPI, Depends, Request, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import models, schemas
import base64
from app.claude_service import responder_mensaje, generar_descripcion_desde_foto
from app.whatsapp_service import enviar_mensaje_texto, extraer_mensaje_entrante

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Phenex Fashion - Asistente IA")

# Permite que el panel admin (React, corriendo en otro puerto/dominio) llame a esta API.
# En producción, reemplazá "*" por el dominio real del panel admin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "phenex_verify_123")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "cambiar-esta-clave")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "phenex-token-cambiar-en-produccion")


class LoginRequest(BaseModel):
    usuario: str
    password: str


@app.post("/auth/login")
def login(datos: LoginRequest):
    """Login simple del panel admin. Devuelve un token que el panel guarda y
    manda en cada request. Pensado para un equipo chico; si en el futuro suman
    más personas con permisos distintos, esto se reemplaza por un sistema de
    usuarios real con contraseñas propias por persona."""
    if datos.usuario != ADMIN_USER or datos.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return {"token": ADMIN_TOKEN}


def verificar_token(authorization: str = Header(None)):
    """Dependencia que protege los endpoints del panel admin."""
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="No autorizado")
    return True


@app.post("/productos/upload-imagen")
async def subir_imagen(file: UploadFile = File(...), _=Depends(verificar_token)):
    """
    Sube una foto de producto y devuelve la URL pública.
    Nota: esto guarda el archivo en disco local, lo cual sirve para desarrollo,
    pero en Render el disco no es persistente entre despliegues. Para producción
    real conviene migrar esto a Cloudinary o S3 (misma firma de función, solo
    cambia dónde se guarda el archivo).
    """
    extension = file.filename.split(".")[-1]
    nombre_archivo = f"{uuid.uuid4()}.{extension}"
    ruta = f"static/uploads/{nombre_archivo}"

    with open(ruta, "wb") as f:
        contenido = await file.read()
        f.write(contenido)

    return {"url": f"{BASE_URL}/static/uploads/{nombre_archivo}"}


@app.post("/productos/generar-descripcion")
async def generar_descripcion(file: UploadFile = File(...), nombre_producto: str = "", _=Depends(verificar_token)):
    """Analiza una foto recién subida y devuelve una descripción sugerida por IA."""
    contenido = await file.read()
    imagen_base64 = base64.b64encode(contenido).decode("utf-8")
    media_type = file.content_type or "image/jpeg"

    descripcion = generar_descripcion_desde_foto(imagen_base64, media_type, nombre_producto)
    return {"descripcion": descripcion}


@app.get("/productos/{producto_id}", response_model=schemas.ProductoOut)
def obtener_producto(producto_id: int, db: Session = Depends(get_db), _=Depends(verificar_token)):
    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@app.delete("/productos/{producto_id}")
def borrar_producto(producto_id: int, db: Session = Depends(get_db), _=Depends(verificar_token)):
    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.activo = False
    db.commit()
    return {"status": "desactivado"}


# ---------- PRODUCTOS (para tu panel admin) ----------

@app.post("/productos", response_model=schemas.ProductoOut)
def crear_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db), _=Depends(verificar_token)):
    nuevo = models.Producto(
        nombre=producto.nombre,
        categoria=producto.categoria,
        descripcion=producto.descripcion,
        precio=producto.precio,
        fotos=producto.fotos,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    for v in producto.variantes:
        db.add(models.Stock(
            producto_id=nuevo.id,
            talle=v.talle,
            color=v.color,
            cantidad_disponible=v.cantidad_disponible
        ))
    db.commit()
    return nuevo


@app.get("/productos", response_model=list[schemas.ProductoOut])
def listar_productos(db: Session = Depends(get_db), _=Depends(verificar_token)):
    return db.query(models.Producto).filter(models.Producto.activo == True).all()


# ---------- WHATSAPP WEBHOOK ----------

@app.get("/webhooks/whatsapp")
def verificar_webhook(request: Request):
    """Meta llama a este endpoint UNA vez, al configurar el webhook, para verificar que sos vos."""
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@app.post("/webhooks/whatsapp")
async def recibir_mensaje_whatsapp(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    numero, texto = extraer_mensaje_entrante(payload)

    if not numero or not texto:
        return {"status": "ignorado"}  # era un status update, no un mensaje

    # Buscar o crear cliente por número de WhatsApp
    cliente = db.query(models.Cliente).filter(
        models.Cliente.canal == "whatsapp",
        models.Cliente.identificador_canal == numero
    ).first()
    if not cliente:
        cliente = models.Cliente(canal="whatsapp", identificador_canal=numero)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    # Buscar o crear la conversación (para mantener contexto)
    conversacion = db.query(models.Conversacion).filter(
        models.Conversacion.cliente_id == cliente.id
    ).first()
    if not conversacion:
        conversacion = models.Conversacion(cliente_id=cliente.id, canal="whatsapp", historial=[])
        db.add(conversacion)
        db.commit()
        db.refresh(conversacion)

    # Le pasamos el cliente_id a Claude vía el mensaje para que pueda armar el pedido
    mensaje_con_contexto = f"[cliente_id={cliente.id}] {texto}"

    respuesta, historial_actualizado = responder_mensaje(
        db, conversacion.historial or [], mensaje_con_contexto
    )

    conversacion.historial = historial_actualizado
    db.commit()

    await enviar_mensaje_texto(numero, respuesta)
    return {"status": "ok"}


# ---------- WEBHOOK DE MERCADOPAGO (confirmación de pago) ----------

@app.post("/webhooks/mercadopago")
async def recibir_notificacion_pago(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    # Acá se consulta el pago con el SDK de MercadoPago usando data["data"]["id"],
    # se confirma que esté aprobado, se busca el pedido por external_reference,
    # se marca como "pagado" y se descuenta el stock reservado definitivamente.
    # (dejo el detalle completo para cuando lleguemos a esa fase)
    return {"status": "recibido"}
