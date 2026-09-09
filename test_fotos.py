from db import conexion

print("FOTOS GUARDADAS")
print("=" * 50)

with conexion() as conn:
    rows = conn.execute(
        """
        SELECT
            id,
            usuario_id,
            fecha,
            tipo,
            telegram_file_id,
            observaciones
        FROM fotos_progreso
        ORDER BY id DESC
        """
    ).fetchall()

    if not rows:
        print("No hay fotos registradas.")
    else:
        for foto in rows:
            print(
                f"ID: {foto['id']}\n"
                f"Usuario: {foto['usuario_id']}\n"
                f"Fecha: {foto['fecha']}\n"
                f"Tipo: {foto['tipo']}\n"
                f"File ID: {foto['telegram_file_id']}\n"
                f"Observaciones: {foto['observaciones']}\n"
                f"{'-' * 50}"
            )
            