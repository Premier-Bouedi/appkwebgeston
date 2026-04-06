import sqlite3
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional, Any

class DatabaseManager:
    """Connexion SQLite + Moteur d'Adaptabilité Universelle (Plug & Play)."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Connexion SQLite standard pour les opérations unitaires
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        # Moteur SQLAlchemy pour les migrations de DataFrames (to_sql)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.create_tables()

    def create_tables(self) -> None:
        query = """
        CREATE TABLE IF NOT EXISTS ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit TEXT NOT NULL,
            prix_unitaire REAL NOT NULL,
            quantite INTEGER NOT NULL,
            age_client INTEGER NOT NULL,
            date_vente TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def sync_any_dataframe(self, df: pd.DataFrame, table_name: str = "stock_client") -> str:
        """
        Migre dynamiquement n'importe quel DataFrame vers SQL.
        Sécurité : Archivage (backup) si la table existe déjà.
        Performance : Indexation automatique sur la colonne 0.
        """
        if df.empty:
            return "DataFrame vide, rien à synchroniser."

        try:
            with self.engine.connect() as conn:
                # 1. Double Sécurité : Archivage de l'ancien stock
                table_exists = conn.execute(
                    text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                ).fetchone()

                if table_exists:
                    backup_name = f"{table_name}_backup"
                    conn.execute(text(f"DROP TABLE IF EXISTS {backup_name}"))
                    conn.execute(text(f"ALTER TABLE {table_name} RENAME TO {backup_name}"))

                # 2. Migration Automatique (Plug & Play)
                df.to_sql(table_name, con=self.engine, if_exists="replace", index=False)

                # 3. Indexation Dynamique pour Performance Zero-Lag
                first_col = df.columns[0]
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_ref ON {table_name} (\"{first_col}\")"))
                conn.commit()

            return f"✅ Succès : {len(df)} lignes synchronisées dans '{table_name}' (avec backup)."
        except Exception as e:
            return f"❌ Erreur de synchronisation : {str(e)}"

    def get_table_data(self, table_name: str = "stock_client") -> pd.DataFrame:
        """Récupère les données d'une table quelconque en DataFrame."""
        try:
            return pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
        except Exception:
            return pd.DataFrame()

    def ajouter_vente(
        self,
        produit: str,
        prix: float,
        qte: int,
        age: int,
    ) -> None:
        query = """
        INSERT INTO ventes (produit, prix_unitaire, quantite, age_client, date_vente)
        VALUES (?, ?, ?, ?, date('now'))
        """
        self.conn.execute(
            query,
            (produit.strip() or "Sans nom", float(prix), int(qte), int(age)),
        )
        self.conn.commit()

    def supprimer_vente(self, vente_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM ventes WHERE id = ?", (int(vente_id),))
        self.conn.commit()
        return cur.rowcount > 0

    def get_all_data(self) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM ventes ORDER BY id", self.conn)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
