"""Esquema SQL: definicion de todas las tablas."""

SCRIPT_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    telegram_id INTEGER UNIQUE,

    nombre TEXT NOT NULL,

    edad INTEGER,
    sexo TEXT,
    altura_cm REAL,

    peso_inicial_kg REAL,
    grasa_inicial_pct REAL,

    pin_hash TEXT,

    codigo_invitacion TEXT UNIQUE,

    rol TEXT NOT NULL CHECK (rol IN ('entrenador','alumno')),

    fecha_registro TEXT NOT NULL DEFAULT (datetime('now')),

    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS medidas_corporales (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL,
    fecha       TEXT NOT NULL DEFAULT (datetime('now')),
    peso_kg     REAL,
    grasa_pct   REAL,
    pecho       REAL,
    cintura     REAL,
    abdomen     REAL,
    cadera      REAL,
    brazo       REAL,
    muslo       REAL,
    pantorrilla REAL,
    hombros     REAL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS ejercicios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT UNIQUE NOT NULL,
    categoria       TEXT NOT NULL CHECK (categoria IN ('fuerza','cardio','movilidad')),
    musculo_principal TEXT
);

CREATE TABLE IF NOT EXISTS rutinas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    creada_por  INTEGER NOT NULL,
    activa      INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (creada_por) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS rutina_ejercicios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rutina_id       INTEGER NOT NULL,
    ejercicio_id    INTEGER NOT NULL,
    orden           INTEGER NOT NULL,
    series_objetivo INTEGER,
    reps_objetivo   INTEGER,
    peso_objetivo   REAL,
    FOREIGN KEY (rutina_id) REFERENCES rutinas(id),
    FOREIGN KEY (ejercicio_id) REFERENCES ejercicios(id)
);

CREATE TABLE IF NOT EXISTS sesiones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL,
    rutina_id       INTEGER,
    fecha           TEXT NOT NULL DEFAULT (datetime('now')),
    duracion_min    INTEGER,
    notas           TEXT,
    completada      INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (rutina_id) REFERENCES rutinas(id)
);

CREATE TABLE IF NOT EXISTS sesion_series (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id       INTEGER NOT NULL,
    ejercicio_id    INTEGER NOT NULL,
    numero_serie    INTEGER NOT NULL,
    reps            INTEGER NOT NULL,
    peso_kg         REAL,
    es_record       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id),
    FOREIGN KEY (ejercicio_id) REFERENCES ejercicios(id)
);

CREATE TABLE IF NOT EXISTS registros_cardio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL,
    fecha           TEXT NOT NULL DEFAULT (datetime('now')),
    distancia_km    REAL,
    tiempo_min      REAL,
    ritmo_promedio  TEXT,
    fc_promedio     INTEGER,
    fc_max          INTEGER,
    cadencia        INTEGER,
    vo2_estimado    REAL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS mediciones_rendimiento (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL,
    fecha           TEXT NOT NULL DEFAULT (datetime('now')),
    fuerza          REAL,
    resistencia     REAL,
    potencia        REAL,
    velocidad       REAL,
    flexibilidad    REAL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS preferencias_alertas (
    usuario_id      INTEGER PRIMARY KEY,
    hora_alerta     TEXT NOT NULL DEFAULT '06:00',
    activa          INTEGER NOT NULL DEFAULT 1,
    mensajes_count  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS fotos_progreso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario_id INTEGER NOT NULL,

    fecha TEXT NOT NULL DEFAULT (datetime('now')),

    tipo TEXT NOT NULL,

    telegram_file_id TEXT NOT NULL,

    observaciones TEXT,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS objetivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario_id INTEGER NOT NULL,

    tipo TEXT NOT NULL,

    valor_objetivo REAL NOT NULL,

    fecha_creacion TEXT NOT NULL DEFAULT (datetime('now')),

    activo INTEGER NOT NULL DEFAULT 1,

    FOREIGN KEY(usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- notificaciones

CREATE TABLE IF NOT EXISTS notificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario_id INTEGER NOT NULL,

    mensaje TEXT NOT NULL,

    leida INTEGER NOT NULL DEFAULT 0,

    fecha TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY(usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS entrenador_alumno (
    entrenador_id INTEGER NOT NULL,
    alumno_id INTEGER NOT NULL,

    PRIMARY KEY (
        entrenador_id,
        alumno_id
    ),

    FOREIGN KEY(entrenador_id)
        REFERENCES usuarios(id),

    FOREIGN KEY(alumno_id)
        REFERENCES usuarios(id)
);

"""

# Catalogo inicial de rutinas fijas
RUTINAS_FIJAS = [
    "Fuerza - Tren Superior",
    "Fuerza - Tren Inferior",
    "Fuerza - Espalda",
    "Fuerza - Cuerpo Completo",
    "Cardio Suave",
    "Cardio Intenso",
    "Movilidad",
]

# Catalogo inicial de ejercicios comunes
EJERCICIOS_BASE = [
    # Fuerza - Tren Superior
    ("Press banca", "fuerza", "pecho"),
    ("Press militar", "fuerza", "hombros"),
    ("Remo con barra", "fuerza", "espalda"),
    ("Curl de biceps", "fuerza", "biceps"),
    ("Extension triceps", "fuerza", "triceps"),
    ("Aperturas", "fuerza", "pecho"),
    # Fuerza - Tren Inferior
    ("Sentadilla", "fuerza", "cuadriceps"),
    ("Peso muerto", "fuerza", "cadena posterior"),
    ("Prensa", "fuerza", "pierna"),
    ("Zancadas", "fuerza", "pierna"),
    ("Curl femoral", "fuerza", "femorales"),
    ("Elevacion gemelos", "fuerza", "gemelos"),
    # Espalda
    ("Dominadas", "fuerza", "espalda"),
    ("Remo en polea", "fuerza", "espalda"),
    ("Pullover", "fuerza", "espalda"),
    # Cardio
    ("Carrera continua", "cardio", "sistema cardiovascular"),
    ("Intervalos", "cardio", "sistema cardiovascular"),
    ("Bicicleta", "cardio", "sistema cardiovascular"),
    ("Eliptica", "cardio", "sistema cardiovascular"),
    # Movilidad
    ("Estiramiento general", "movilidad", "cuerpo completo"),
    ("Yoga", "movilidad", "cuerpo completo"),
    ("Foam roller", "movilidad", "cuerpo completo"),
]


def seed_catalogos(conn) -> None:
    """Inserta rutinas y ejercicios base si las tablas estan vacias."""
    cur = conn.cursor()

    # Ejercicios
    cur.execute("SELECT COUNT(*) FROM ejercicios")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO ejercicios (nombre, categoria, musculo_principal) VALUES (?, ?, ?)",
            EJERCICIOS_BASE,
        )

    # Las rutinas fijas las crea el entrenador desde el bot
