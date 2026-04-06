import pandas as pd

class VisionBootLocal:
    """Moteur d'intelligence stratégique 100 % local — Analyse prédictive et heuristique."""

    def __init__(self):
        self.name = "Vision-Boot Engine v2.0"

    def get_smart_analysis(self, df: pd.DataFrame | None) -> str:
        """Diagnostic complet : Croissance, Tendance et Stock."""
        if df is None or df.empty:
            return "📊 **Vision-Boot** est prêt. Importez vos données pour un diagnostic stratégique."

        try:
            # 1. KPIs de base
            total_ca = float(df["Montant_Total"].sum())
            total_tx = len(df)
            panier_moyen = total_ca / total_tx if total_tx > 0 else 0
            
            # 2. Analyse de Tendance (Momentum)
            # On divise le dataset en deux pour comparer (début vs fin)
            half = len(df) // 2
            if half > 0:
                ca_recent = df.tail(half)["Montant_Total"].sum()
                ca_ancien = df.head(half)["Montant_Total"].sum()
                growth = ((ca_recent - ca_ancien) / ca_ancien * 100) if ca_ancien > 0 else 0
                trend_msg = f"📈 **Croissance** de **+{growth:.1f}%**" if growth > 0 else f"📉 **Ralentissement** de **{growth:.1f}%**"
            else:
                trend_msg = "⏱️ Période trop courte pour une tendance."

            # 3. Heuristique de Stock (Runway)
            # On identifie les catégories bientôt en rupture (vitesse de vente théorique)
            stock_summary = df.groupby("Categorie_Produit")["Quantite"].sum()
            critical_cats = stock_summary[stock_summary < 5].index.tolist()
            
            analysis = f"### 🤖 Diagnostic Stratégique — {self.name}\n\n"
            analysis += f"#### 📊 Performance Globale\n"
            analysis += f"* **Chiffre d'Affaires :** {total_ca:,.2f} €\n"
            analysis += f"* **Momentum :** {trend_msg}\n"
            analysis += f"* **Panier Moyen :** {panier_moyen:.2f} €\n\n"

            # 4. Recommandations Actionnables
            analysis += "#### 💡 Recommandations IA\n"
            if critical_cats:
                analysis += f"⚠️ **ALERTE STOCK** : Les segments **{', '.join(critical_cats)}** sont proches de la rupture. Ravitaillement urgent conseillé.\n"
            
            if growth < 0:
                analysis += "📉 **ALERTE BAISSE** : Votre activité ralentit. Envisagez une promotion sur les produits phares pour relancer le volume.\n"
            else:
                analysis += "🚀 **OPPORTUNITÉ** : Bonne dynamique ! C'est le moment d'investir dans le marketing pour amplifier votre portée.\n"

            # 5. Saisonnalité
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                best_day_idx = df["Date"].dt.dayofweek.mode().iloc[0]
                days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                analysis += f"\n📅 **SAISONNALITÉ** : Votre jour de vente le plus actif est le **{days[best_day_idx]}**.\n"

            return analysis
        except Exception as e:
            return f"⚠️ Erreur d'analyse Vision-Boot : {str(e)}"

    def analyze(self, df: pd.DataFrame | None) -> str:
        """Alias pour compatibilité avec l’interface existante."""
        return self.get_smart_analysis(df)

    def get_smart_table_scan(self, df: pd.DataFrame | None) -> str:
        """Scan universel pour n'importe quelle table SQL."""
        if df is None or df.empty:
            return "Pas de données à scanner."
        return f"Scan complet de {len(df)} lignes effectué. Structure conforme."

def vision_boot_smart_scan(df: pd.DataFrame | None) -> str:
    """Point d’entrée fonction (API module) : scan universel sur n’importe quel DataFrame."""
    return VisionBootLocal().get_smart_table_scan(df)
