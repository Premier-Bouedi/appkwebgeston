import pandas as pd

class VisionBootLocal:
    """Moteur d'intelligence heuristique 100 % local — aucune clé ni appel réseau."""

    def __init__(self):
        self.name = "Vision-Boot 2.0"

    def _colonnes_produit(self, df: pd.DataFrame) -> str:
        if "Produit" in df.columns:
            return "Produit"
        if "Categorie_Produit" in df.columns:
            return "Categorie_Produit"
        return ""

    def get_smart_analysis(self, df: pd.DataFrame | None) -> str:
        """Analyse automatique des données sans aucune connexion externe."""
        if df is None or df.empty:
            return (
                "📊 **Vision-Boot** est prêt. Importez un fichier CSV depuis la barre latérale "
                "pour obtenir un diagnostic détaillé de votre activité."
            )

        try:
            if "Montant_Total" not in df.columns:
                return (
                    "Les données chargées ne contiennent pas encore le champ nécessaire à l’analyse "
                    "(`Montant_Total`). Vérifiez que votre fichier suit le modèle proposé."
                )

            total_ca = float(df["Montant_Total"].sum())
            panier_moyen = float(df["Montant_Total"].mean())

            col_prod = self._colonnes_produit(df)
            if col_prod:
                mode_s = df[col_prod].mode()
                top_produit = str(mode_s.iloc[0]) if len(mode_s) else "—"
            else:
                top_produit = "—"

            if "Âge_Client" in df.columns:
                top_client_age = df.groupby("Âge_Client")["Montant_Total"].sum().idxmax()
                try:
                    age_str = str(int(top_client_age))
                except (TypeError, ValueError):
                    age_str = str(top_client_age)
            else:
                age_str = "—"

            analysis = f"### 🤖 Diagnostic de {self.name}\n\n"
            analysis += "J'ai analysé votre base de données. Voici votre bilan actuel :\n"
            analysis += f"* **Chiffre d'Affaires :** {total_ca:,.2f} €\n"
            analysis += f"* **Panier Moyen :** {panier_moyen:.2f} €\n\n"

            analysis += (
                f"🟢 **[OPPORTUNITÉ]** : Votre client idéal a environ **{age_str} ans**. "
                f"C'est sur cette tranche d'âge que vous réalisez le meilleur cumul de CA "
                f"avec le produit / segment **{top_produit}**.\n\n"
            )

            if panier_moyen > 150:
                analysis += (
                    "💎 **[PROFIL LUXE]** : Vos clients achètent peu mais cher. "
                    "Misez sur l'exclusivité.\n"
                )
            elif panier_moyen < 50:
                analysis += (
                    "📦 **[PROFIL VOLUME]** : Vos marges unitaires sont modestes. "
                    "Il faut viser la quantité de ventes.\n"
                )
            else:
                analysis += (
                    "⚖️ **[PROFIL ÉQUILIBRÉ]** : Votre business est stable. Optimisez vos stocks.\n"
                )

            return analysis
        except Exception:
            return (
                "Vision-Boot n’a pas pu terminer l’analyse sur ce jeu de données. "
                "Vérifiez les colonnes attendues (schéma e-commerce) et réessayez après import."
            )

    def analyze(self, df: pd.DataFrame | None) -> str:
        """Alias pour compatibilité avec l’interface existante."""
        return self.get_smart_analysis(df)

    def get_smart_table_scan(self, df: pd.DataFrame | None) -> str:
        """Analyse heuristique d'une table quelconque (colonnes et types inconnus à l'avance)."""
        if df is None or df.empty:
            return "### 🤖 Vision-Boot — scan universel\n\nAucune ligne à analyser."

        try:
            n, m = len(df), len(df.columns)
            lines: list[str] = [
                f"### 🤖 Vision-Boot — scan universel\n\n",
                f"* **Lignes :** {n:,} · **Colonnes :** {m}\n",
            ]

            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            dt_cols = [
                c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])
            ]
            obj_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

            if num_cols:
                preferred: str | None = None
                for kw in (
                    "montant", "total", "prix", "ca", "amount", "qty", "quantite", "quantité", "stock", "valeur",
                ):
                    for c in num_cols:
                        if kw in c.lower():
                            preferred = c
                            break
                    if preferred:
                        break
                col = preferred or num_cols[0]
                s = pd.to_numeric(df[col], errors="coerce")
                total = float(s.sum())
                mean = float(s.mean()) if len(s) else 0.0
                lines.append(
                    f"\n🟢 **[INFO]** Colonne numérique pivot probable : **{col}** "
                    f"(somme ≈ **{total:,.2f}**, moyenne ≈ **{mean:,.2f}**).\n"
                )
            else:
                lines.append(
                    "\n⚠️ **Profil plutôt textuel / qualitatif** — peu de colonnes numériques détectées.\n"
                )

            if obj_cols:
                sample_col = obj_cols[0]
                nu = int(df[sample_col].nunique(dropna=True))
                lines.append(
                    f"* **Diversité ({sample_col})** : {nu} valeur(s) distincte(s).\n"
                )

            if dt_cols:
                lines.append(
                    f"* **Colonnes temporelles** : {', '.join(dt_cols)} — utile pour séries ou filtres.\n"
                )

            return "".join(lines)
        except Exception:
            return (
                "### 🤖 Vision-Boot — scan universel\n\n"
                "L’analyse automatique n’a pas pu se terminer sur cette structure de table."
            )

def vision_boot_smart_scan(df: pd.DataFrame | None) -> str:
    """Point d’entrée fonction (API module) : scan universel sur n’importe quel DataFrame."""
    return VisionBootLocal().get_smart_table_scan(df)
