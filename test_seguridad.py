from db import conexion

with conexion() as conn:
    usuarios = conn.execute(
        """
        SELECT id, telegram_id, nombre, rol, activo
        FROM usuarios
        ORDER BY id
        """
    ).fetchall()

print("USUARIOS:")

for usuario in usuarios:
    print(
        f"ID={usuario['id']} | "
        f"Nombre={usuario['nombre']} | "
        f"Rol={usuario['rol']} | "
        f"Activo={usuario['activo']}"
    )