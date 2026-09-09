from db import init_db, conexion

print("Inicializando base de datos...")

init_db()

print("OK Base de datos inicializada.")

with conexion() as conn:
    tablas = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    print("\nTablas:")
    for tabla in tablas:
        print(f"  - {tabla['name']}")

    usuarios = conn.execute(
        "SELECT id, nombre, rol, activo FROM usuarios"
    ).fetchall()

    print(f"\nUsuarios registrados: {len(usuarios)}")

    for usuario in usuarios:
        print(
            f"  #{usuario['id']} - "
            f"{usuario['nombre']} - "
            f"{usuario['rol']} - "
            f"activo={usuario['activo']}"
        )

print("\nOK")
