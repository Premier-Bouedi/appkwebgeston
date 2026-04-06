"""
Connecteur SQL agnostique (SaaS) : MySQL, PostgreSQL, SQL Server, SQLite, etc.
via une même API orientée objet (SQLAlchemy).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import Engine


class VisionDatabase:
    """Lecture du schéma client, import DataFrame, exécution SQL paramétrée."""

    def __init__(self, connection_string: str, *, pool_pre_ping: bool = True) -> None:
        self.connection_string = connection_string
        self.engine: Engine = create_engine(connection_string, pool_pre_ping=pool_pre_ping)
        self.metadata = MetaData()
        self.inspector = inspect(self.engine)

    def tester_connexion(self) -> tuple[bool, str]:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Connexion établie."
        except Exception as e:
            return False, str(e)

    def lister_schemas(self) -> list[str]:
        try:
            return sorted(s for s in self.inspector.get_schema_names() if s not in ("information_schema",))
        except Exception:
            return []

    def lister_tables(self, schema: str | None = None) -> list[str]:
        return sorted(self.inspector.get_table_names(schema=schema))

    def lire_table(
        self,
        table_name: str,
        schema: str | None = None,
        max_rows: int | None = 10_000,
    ) -> pd.DataFrame:
        """
        Charge une table en DataFrame. Si max_rows est un entier > 0, limite le volume
        (recommandé pour les très grosses tables SaaS).
        """
        if max_rows is None or max_rows <= 0:
            return pd.read_sql_table(table_name, self.engine, schema=schema)

        meta = MetaData()
        meta.reflect(bind=self.engine, schema=schema, only=[table_name])
        if not meta.tables:
            raise ValueError(f"Table introuvable ou inaccessible : {table_name!r}")
        table = next(iter(meta.tables.values()))
        stmt = select(table).limit(int(max_rows))
        return pd.read_sql(stmt, self.engine)

    def ecrire_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        *,
        if_exists: str = "replace",
        schema: str | None = None,
        chunksize: int = 500,
    ) -> None:
        """Réécrit la table à partir du DataFrame (idem pandas.to_sql)."""
        df.to_sql(
            table_name,
            self.engine,
            if_exists=if_exists,
            index=False,
            schema=schema,
            chunksize=chunksize,
        )

    def executer_commande(self, sql_query: str) -> None:
        """Exécute une instruction SQL (DDL/DML). À n'utiliser qu'avec des requêtes de confiance."""
        with self.engine.begin() as conn:
            conn.execute(text(sql_query))
