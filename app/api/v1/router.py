from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    clientes,
    cuentas,
    empresas,
    gastos,
    inventario,
    productos,
    proveedores,
    reportes,
    resumen,
    ventas,
)

api_router = APIRouter()

# Nota: los routers de vehiculos/historico/catalogos (modulo Mantenimiento/
# Reparacion del proyecto anterior, a1-gestion-talleres) se retiraron de la
# API de este proyecto (Kaudal, exclusivo para ventas/cuentas/reportes): no
# se necesitan aqui. Los modelos, migraciones y endpoints siguen en el
# codigo por si se reutilizan, simplemente no estan expuestos.
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
api_router.include_router(empresas.router, prefix="/empresas", tags=["empresas"])
api_router.include_router(productos.router, prefix="/productos", tags=["productos"])
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["proveedores"])
api_router.include_router(inventario.router, prefix="/inventario", tags=["inventario"])
api_router.include_router(ventas.router, prefix="/ventas", tags=["ventas"])
api_router.include_router(gastos.router, prefix="/gastos", tags=["gastos"])
api_router.include_router(cuentas.router, prefix="/cuentas", tags=["cuentas"])
api_router.include_router(resumen.router, prefix="/resumen", tags=["resumen"])
api_router.include_router(reportes.router, prefix="/reportes", tags=["reportes"])


@api_router.get("/ping", tags=["health"])
def ping() -> dict[str, str]:
    return {"ping": "pong"}
