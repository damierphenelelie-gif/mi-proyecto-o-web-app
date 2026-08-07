# Publicar el panel en la web (Vercel)

## 1. Subir el código a GitHub

```bash
cd phenex-admin
git init
git add .
git commit -m "Panel admin Phenex Fashion"
```

Creá un repo nuevo en GitHub (podés dejarlo privado) y subilo:
```bash
git remote add origin https://github.com/TU_USUARIO/phenex-admin.git
git push -u origin main
```

## 2. Deploy en Vercel

1. Entrá a https://vercel.com y creá cuenta con tu GitHub.
2. "Add New Project" → elegís el repo `phenex-admin`.
3. Vercel detecta automáticamente que es un proyecto Vite/React, no hay que tocar nada.
4. Antes de darle "Deploy", agregá la variable de entorno:
   - `VITE_API_URL` = la URL de tu backend en Render (ej: `https://phenex-backend.onrender.com`)
5. "Deploy". En 1-2 minutos te da una URL tipo `phenex-admin.vercel.app`.

## 3. Dominio propio (opcional)

En el proyecto de Vercel → Settings → Domains → agregás `admin.phenexfashion.com`
(o el que quieras) y seguís las instrucciones para apuntar el DNS desde donde
compraste el dominio.

## 4. Instalarlo como app en el celular (PWA)

Con el panel ya andando en su URL de Vercel (tiene que ser HTTPS, Vercel lo da
automático):

- **Android**: abrís la URL en Chrome → menú (⋮) → "Agregar a la pantalla de inicio".
- **iPhone**: abrís la URL en Safari → botón compartir → "Agregar a pantalla de inicio".

Te queda un ícono con el logo de Phenex que abre en pantalla completa, sin la
barra del navegador — se siente como una app nativa aunque técnicamente es web.

## 5. Actualizar el backend con las claves del login

En Render, en las variables de entorno del backend, asegurate de tener
configurados `ADMIN_USER`, `ADMIN_PASSWORD` y `ADMIN_TOKEN` con valores reales
(no los de ejemplo del `.env.example`) antes de que tu equipo empiece a usarlo.

## Nota sobre CORS

El backend ahora acepta pedidos desde cualquier origen (`allow_origins=["*"]`)
para que puedas probar fácil. Cuando ya tengas la URL final de Vercel, conviene
restringirlo en `app/main.py` a solo esa URL, así nadie más puede llamar a tu
API desde otro sitio.
