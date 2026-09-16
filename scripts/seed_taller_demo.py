"""Datos de ejemplo del taller para la empresa demo (ver seed_test_users.py):
un cliente, un vehiculo, catalogos de mantenimiento/reparacion, y su
historico. Basado en los datos de muestra de collections.txt (Firestore).

Uso:
    python scripts/seed_test_users.py   # primero: crea la empresa DEMO
    python scripts/seed_taller_demo.py

Idempotente: si el vehiculo de ejemplo ya existe, no vuelve a crear nada.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Cliente,
    Empresa,
    HistoricoMantenimiento,
    HistoricoReparacion,
    Role,
    TipoMantenimiento,
    TipoReparacion,
    User,
    Vehiculo,
)

EMPRESA_CODIGO = "DEMO"

PLACA = "ABC-123"

TIPOS_MANTENIMIENTO = [
    ("Intermedio", "Cambio de aceite"),
    ("Intermedio", "Cambio de bujias"),
    ("Intermedio", "Cambio de aire"),
    ("Completo", "Cambio de frenos"),
]

TIPOS_REPARACION = [
    "electronico",
    "mecanica",
    "planchado",
    "pintura",
    "electrico",
]

HISTORICO_MANTENIMIENTO = [
    # (fecha, km, tipo, cambios, costo)
    (date(2026, 2, 4), 5000, "Completo", ["Cambio de frenos"], 800),
    (
        date(2026, 3, 10),
        20000,
        "Completo",
        ["Cambio de aceite", "Cambio de bujias", "Cambio de aire"],
        250.65,
    ),
    (date(2026, 3, 24), 30000, "Intermedio", ["Cambio de aceite", "Cambio de bujias"], 1000),
    (date(2026, 3, 25), 30000, "Intermedio", ["Cambio de aceite", "Cambio de bujias"], 1000),
    (date(2026, 3, 28), 30000, "Intermedio", ["Cambio de aceite", "Cambio de bujias"], 1000),
]

HISTORICO_REPARACIONES = [
    (date(2026, 3, 14), 13000, ["mecanica"], "Se reparo el motor", 300),
    (
        date(2026, 3, 25),
        30000,
        ["mecanica", "electronico"],
        "Se cambio el motor, se hizo un taller mecanico etc",
        1000,
    ),
]


def main() -> None:
    with SessionLocal() as db:
        empresa = db.scalar(select(Empresa).where(Empresa.codigo == EMPRESA_CODIGO))
        if empresa is None:
            raise SystemExit(
                f"No existe la empresa '{EMPRESA_CODIGO}'. "
                "Ejecuta primero: python scripts/seed_test_users.py"
            )

        for categoria, nombre in TIPOS_MANTENIMIENTO:
            existe = db.scalar(
                select(TipoMantenimiento).where(
                    TipoMantenimiento.empresa_id == empresa.id,
                    TipoMantenimiento.categoria == categoria,
                    TipoMantenimiento.nombre == nombre,
                )
            )
            if existe is None:
                db.add(
                    TipoMantenimiento(
                        empresa_id=empresa.id, categoria=categoria, nombre=nombre
                    )
                )

        for nombre in TIPOS_REPARACION:
            existe = db.scalar(
                select(TipoReparacion).where(
                    TipoReparacion.empresa_id == empresa.id,
                    TipoReparacion.nombre == nombre,
                )
            )
            if existe is None:
                db.add(TipoReparacion(empresa_id=empresa.id, nombre=nombre))

        db.flush()

        super_admin = db.scalar(
            select(User)
            .join(Role)
            .where(User.empresa_id == empresa.id, Role.code == "super_admin")
        )
        if super_admin is None:
            raise SystemExit(
                f"La empresa '{EMPRESA_CODIGO}' no tiene super_admin. "
                "Ejecuta primero: python scripts/seed_test_users.py"
            )

        vehiculo = db.scalar(
            select(Vehiculo).where(
                Vehiculo.empresa_id == empresa.id, Vehiculo.placa == PLACA
            )
        )
        if vehiculo is not None:
            db.commit()
            print(f"El vehiculo de ejemplo {PLACA} ya existe. Nada mas que hacer.")
            return

        cliente = Cliente(
            empresa_id=empresa.id,
            tip_documento="DNI",
            num_documento="72257720",
            nombres="Jesus",
            apellidos="Cotrina",
            correo="jesuscotrin@gmail.com",
            telefono="949581986",
            fec_nacimiento=date(2000, 7, 27),
        )
        db.add(cliente)
        db.flush()

        vehiculo = Vehiculo(
            empresa_id=empresa.id,
            cliente_id=cliente.id,
            placa=PLACA,
            marca="Toyota",
            modelo="Urus",
            carroceria="4x4",
            num_motor="12345678",
            vin_serie="87654321",
        )
        db.add(vehiculo)
        db.flush()

        for fecha, km, tipo, cambios, costo in HISTORICO_MANTENIMIENTO:
            db.add(
                HistoricoMantenimiento(
                    empresa_id=empresa.id,
                    vehiculo_id=vehiculo.id,
                    usuario_id=super_admin.id,
                    fec_mantenimiento=fecha,
                    kilometraje=km,
                    tipo_mantenimiento=tipo,
                    cambios_realizados=cambios,
                    costo=costo,
                )
            )

        for fecha, km, reparaciones, nota, costo in HISTORICO_REPARACIONES:
            db.add(
                HistoricoReparacion(
                    empresa_id=empresa.id,
                    vehiculo_id=vehiculo.id,
                    usuario_id=super_admin.id,
                    fec_reparacion=fecha,
                    kilometraje=km,
                    reparaciones_realizadas=reparaciones,
                    nota=nota,
                    costo=costo,
                )
            )

        db.commit()

    print(f"Datos de ejemplo creados para la empresa '{EMPRESA_CODIGO}': cliente,")
    print(f"vehiculo {PLACA}, catalogos e historico de mantenimiento/reparaciones.")


if __name__ == "__main__":
    main()
