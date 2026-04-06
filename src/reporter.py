from fpdf import FPDF
import datetime
import io
from pathlib import Path

class VisionShopFlowReporter(FPDF):
    def header(self):
        # Logo placeholder or Text
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(46, 204, 113) # Vision-ShopFlow Green
        self.cell(0, 10, 'VISION-SHOPFLOW PREMIUM - RAPPORT D\'ACTIVITÉ', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | Rapport généré par Vision-ShopFlow (Claïnn Magnaga) le {datetime.datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

def generate_full_pdf_report(df, assistant_insight):
    """Génère un rapport PDF complet regroupant statistiques et insights."""
    pdf = VisionShopFlowReporter()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # 1. Résumé Exécutif
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, "1. RÉSUMÉ EXÉCUTIF", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 11)
    total_ca = df['Montant_Total'].sum()
    n_ventes = len(df)
    panier_moyen = total_ca / n_ventes if n_ventes > 0 else 0
    
    pdf.cell(0, 10, f"- Nombre total de transactions : {n_ventes}", 0, 1, 'L')
    pdf.cell(0, 10, f"- Chiffre d'Affaires global : {total_ca:,.2f} EUR", 0, 1, 'L')
    pdf.cell(0, 10, f"- Panier Moyen : {panier_moyen:,.2f} EUR", 0, 1, 'L')
    pdf.ln(10)

    # 2. Insights Vision-Boot
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, "2. DIAGNOSTIC VISION-BOOT", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 11)
    # Nettoyage du markdown pour le PDF (FPDF2 ne gère pas le markdown complexe nativement)
    clean_insight = assistant_insight.replace('**', '').replace('###', '').replace('🟢', '[OPPORTUNITÉ]').replace('🔵', '[INFO]').replace('💡', '[CONSEIL]')
    pdf.multi_cell(0, 7, clean_insight)
    
    pdf.ln(10)

    # 3. Répartition par Catégorie (Tableau simple)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, "3. ANALYSE PAR CATÉGORIE", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(90, 10, "Catégorie", 1, 0, 'C')
    pdf.cell(90, 10, "Revenu (EUR)", 1, 1, 'C')
    
    pdf.set_font('Helvetica', '', 10)
    ca_cat = df.groupby('Categorie_Produit')['Montant_Total'].sum().sort_values(ascending=False)
    for cat, val in ca_cat.items():
        pdf.cell(90, 10, str(cat), 1, 0, 'L')
        pdf.cell(90, 10, f"{val:,.2f}", 1, 1, 'R')

    # Retourner les bytes du PDF
    return pdf.output()
