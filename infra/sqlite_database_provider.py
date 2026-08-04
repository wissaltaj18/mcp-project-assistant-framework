"""Implémentation concrète d'un accès SQLite -- utilisée par query_database/get_database_schema dans ChatTools."""

import sqlite3
from typing import List


class SqliteDatabaseProvider:
    """Accès en lecture/écriture à une base SQLite locale, un fichier par projet/Workspace."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def execute_query(self, query: str) -> List[tuple]:
        """Exécute une requête de LECTURE (SELECT) et renvoie les lignes."""
        connexion = sqlite3.connect(self._db_path)
        try:
            curseur = connexion.execute(query)
            return curseur.fetchall()
        finally:
            connexion.close()

    def execute_write(self, query: str, params: tuple = ()) -> int:
        """Exécute une requête d'ÉCRITURE, renvoie le nombre de lignes affectées."""
        connexion = sqlite3.connect(self._db_path)
        try:
            curseur = connexion.execute(query, params)
            connexion.commit()
            return curseur.rowcount
        finally:
            connexion.close()

    def get_schema(self) -> str:
        """Renvoie les tables et colonnes réellement présentes dans la base."""
        connexion = sqlite3.connect(self._db_path)
        try:
            tables = connexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if not tables:
                return "Aucune table trouvée (base de données vide ou inexistante)."

            lignes = []
            for (nom_table,) in tables:
                colonnes = connexion.execute(f"PRAGMA table_info({nom_table})").fetchall()
                noms_colonnes = ", ".join(col[1] for col in colonnes)
                lignes.append(f"{nom_table}({noms_colonnes})")
            return "\n".join(lignes)
        finally:
            connexion.close()