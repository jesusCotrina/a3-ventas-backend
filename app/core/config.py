from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Por defecto SQLite para poder arrancar sin PostgreSQL.
    # En produccion/desarrollo real: postgresql+psycopg://taller:taller@localhost:5432/taller
    database_url: str = "sqlite+pysqlite:///./dev.db"

    @field_validator("database_url")
    @classmethod
    def _usar_driver_psycopg(cls, v: str) -> str:
        """Proveedores como Render/Heroku entregan la URL de Postgres como
        `postgres://...` o `postgresql://...` (sin driver), que en
        SQLAlchemy 2.0 resuelve a psycopg2 por defecto -- pero este proyecto
        usa psycopg (v3, ver requirements.txt). Sin este arreglo, pegar esa
        URL tal cual en DATABASE_URL revienta al conectar con
        `ModuleNotFoundError: No module named 'psycopg2'`.
        """
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 1 dia
    refresh_token_expire_days: int = 7

    demo_mode: bool = False

    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
