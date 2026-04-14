"""
Service de génération de contrats de prêt en PDF
Utilise ReportLab pour créer des documents professionnels
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Image as RLImage
from io import BytesIO
import os
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


# -------------------------------------------------------
# Color Palette
# -------------------------------------------------------
BRAND_DARK = colors.HexColor('#0D1B2A')
BRAND_BLUE = colors.HexColor('#1565C0')
BRAND_LIGHT_BLUE = colors.HexColor('#E3F2FD')
ACCENT_GREEN = colors.HexColor('#2E7D32')
ACCENT_ORANGE = colors.HexColor('#E65100')
LIGHT_GREY = colors.HexColor('#F5F5F5')
MID_GREY = colors.HexColor('#9E9E9E')
TABLE_HEADER = colors.HexColor('#1565C0')
TABLE_ALT = colors.HexColor('#EEF5FB')


class LoanContractGenerator:
    """Génère un contrat de prêt PDF professionnel"""

    INSTITUTION_NAME = "MicroFinance Platform"
    INSTITUTION_ADDRESS = "Dakar, Sénégal"
    INSTITUTION_PHONE = "+221 33 000 00 00"
    INSTITUTION_EMAIL = "contact@microfinance.sn"
    INSTITUTION_RCCM = "SN-DKR-2024-B-12345"

    def __init__(self, loan):
        self.loan = loan
        self.client = loan.client
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.title_style = ParagraphStyle(
            'ContractTitle',
            parent=self.styles['Title'],
            fontSize=20,
            textColor=BRAND_DARK,
            spaceAfter=6,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        )
        self.subtitle_style = ParagraphStyle(
            'ContractSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=BRAND_BLUE,
            spaceAfter=4,
            fontName='Helvetica',
            alignment=TA_CENTER,
        )
        self.section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            spaceBefore=14,
            spaceAfter=4,
            leftIndent=6,
        )
        self.body_style = ParagraphStyle(
            'ContractBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=BRAND_DARK,
            fontName='Helvetica',
            spaceAfter=4,
            leading=14,
            alignment=TA_JUSTIFY,
        )
        self.bold_style = ParagraphStyle(
            'Bold',
            parent=self.body_style,
            fontName='Helvetica-Bold',
        )
        self.small_style = ParagraphStyle(
            'Small',
            parent=self.body_style,
            fontSize=8,
            textColor=MID_GREY,
        )

    def generate(self):
        """Generate the complete loan contract PDF"""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"Contrat de Prêt {self.loan.loan_number}",
        )

        story = []
        story += self._build_header()
        story += self._build_loan_summary()
        story += self._build_client_section()
        story += self._build_financial_terms()
        story += self._build_amortization_table()
        story += self._build_clauses()
        story += self._build_signatures()

        doc.build(story, onFirstPage=self._add_page_frame,
                  onLaterPages=self._add_page_frame)
        self.buffer.seek(0)
        return self.buffer

    def _add_page_frame(self, canvas, doc):
        """Add header/footer to each page"""
        canvas.saveState()
        width, height = A4

        # Top border bar
        canvas.setFillColor(BRAND_BLUE)
        canvas.rect(0, height - 0.8 * cm, width, 0.8 * cm, fill=True, stroke=False)

        # Institution name in top bar
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(2 * cm, height - 0.55 * cm, self.INSTITUTION_NAME)
        canvas.drawRightString(width - 2 * cm, height - 0.55 * cm,
                               f"Contrat N° {self.loan.loan_number}")

        # Bottom bar
        canvas.setFillColor(BRAND_DARK)
        canvas.rect(0, 0, width, 1 * cm, fill=True, stroke=False)

        # Footer text
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(2 * cm, 0.35 * cm,
                          f"Document confidentiel - {self.INSTITUTION_NAME} - {self.INSTITUTION_ADDRESS}")
        canvas.drawRightString(width - 2 * cm, 0.35 * cm,
                               f"Page {doc.page}")

        canvas.restoreState()

    def _build_header(self):
        elements = [
            Spacer(1, 0.5 * cm),
            Paragraph(self.INSTITUTION_NAME.upper(), self.title_style),
            Paragraph("Plateforme de Microfinance", self.subtitle_style),
            Paragraph(
                f"{self.INSTITUTION_ADDRESS} | Tél: {self.INSTITUTION_PHONE} | {self.INSTITUTION_EMAIL}",
                self.small_style
            ),
            Spacer(1, 0.5 * cm),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE),
            Spacer(1, 0.3 * cm),
            Paragraph(
                "CONTRAT DE PRÊT",
                ParagraphStyle('MainTitle', parent=self.title_style, fontSize=22,
                               textColor=BRAND_DARK, spaceBefore=8)
            ),
            Paragraph(
                f"Réf: <b>{self.loan.loan_number}</b> | Date: <b>{timezone.now().strftime('%d/%m/%Y')}</b>",
                ParagraphStyle('RefDate', parent=self.subtitle_style,
                               fontSize=10, textColor=MID_GREY)
            ),
            HRFlowable(width="100%", thickness=1, color=LIGHT_GREY),
            Spacer(1, 0.5 * cm),
        ]
        return elements

    def _build_loan_summary(self):
        amount = float(self.loan.approved_amount or self.loan.requested_amount)
        schedule = self.loan.get_amortization_schedule()
        total_interest = sum(r['interest'] for r in schedule)
        first_payment = schedule[0]['payment'] if schedule else 0

        summary_data = [
            ['MONTANT DU PRÊT', f"{amount:,.0f} FCFA",
             'DURÉE', f"{self.loan.duration_months} mois"],
            ['TAUX D\'INTÉRÊT', f"{float(self.loan.interest_rate):.2f}% /mois",
             'TAUX ANNUEL', f"{float(self.loan.product.annual_interest_rate):.1f}%"],
            ['MENSUALITÉ', f"{first_payment:,.0f} FCFA",
             'TOTAL INTÉRÊTS', f"{total_interest:,.0f} FCFA"],
            ['FRAIS DE DOSSIER', f"{float(self.loan.processing_fee):,.0f} FCFA",
             'DATE 1ÈRE ÉCHÉANCE',
             self.loan.first_payment_date.strftime('%d/%m/%Y') if self.loan.first_payment_date else 'N/A'],
        ]

        table = Table(summary_data, colWidths=[4.5 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BRAND_LIGHT_BLUE),
            ('BACKGROUND', (0, 0), (0, -1), BRAND_BLUE),
            ('BACKGROUND', (2, 0), (2, -1), BRAND_BLUE),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.white),
            ('TEXTCOLOR', (1, 0), (1, -1), BRAND_DARK),
            ('TEXTCOLOR', (3, 0), (3, -1), BRAND_DARK),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTSIZE', (1, 0), (1, -1), 11),
            ('FONTSIZE', (3, 0), (3, -1), 11),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUND', (0, 0), (-1, -1), [BRAND_LIGHT_BLUE, TABLE_ALT]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        return [table, Spacer(1, 0.5 * cm)]

    def _section_header(self, title):
        header_data = [[Paragraph(f"  {title}", self.section_header_style)]]
        t = Table(header_data, colWidths=[17 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BRAND_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return [t, Spacer(1, 0.2 * cm)]

    def _build_client_section(self):
        elements = self._section_header("ARTICLE 1 — IDENTIFICATION DES PARTIES")

        elements.append(Paragraph(
            "<b>L'Établissement de Microfinance :</b>", self.bold_style
        ))
        inst_data = [
            ['Nom:', self.INSTITUTION_NAME, 'RCCM:', self.INSTITUTION_RCCM],
            ['Adresse:', self.INSTITUTION_ADDRESS, 'Téléphone:', self.INSTITUTION_PHONE],
        ]
        t = Table(inst_data, colWidths=[3 * cm, 6 * cm, 3 * cm, 5 * cm])
        t.setStyle(self._info_table_style())
        elements += [t, Spacer(1, 0.3 * cm)]

        elements.append(Paragraph("<b>L'Emprunteur :</b>", self.bold_style))
        c = self.client
        client_data = [
            ['Nom complet:', c.full_name, 'CNI/Passeport:', c.national_id],
            ['Date de naissance:', c.date_of_birth.strftime('%d/%m/%Y'),
             'Téléphone:', c.phone],
            ['Adresse:', c.address, 'Ville:', c.city],
            ['Activité:', c.get_employment_type_display(), 'Revenus mensuels:',
             f"{float(c.monthly_income):,.0f} FCFA"],
        ]
        t = Table(client_data, colWidths=[3.5 * cm, 5.5 * cm, 3.5 * cm, 4.5 * cm])
        t.setStyle(self._info_table_style())
        elements.append(t)

        if self.loan.guarantor:
            elements += [Spacer(1, 0.2 * cm),
                         Paragraph("<b>Le Garant :</b>", self.bold_style)]
            g = self.loan.guarantor
            g_data = [
                ['Nom complet:', g.full_name, 'CNI:', g.national_id],
                ['Téléphone:', g.phone, 'Relation:', g.relationship],
            ]
            t = Table(g_data, colWidths=[3 * cm, 6 * cm, 3 * cm, 5 * cm])
            t.setStyle(self._info_table_style())
            elements.append(t)

        return elements + [Spacer(1, 0.3 * cm)]

    def _build_financial_terms(self):
        elements = self._section_header("ARTICLE 2 — CONDITIONS FINANCIÈRES DU PRÊT")

        loan = self.loan
        amount = float(loan.approved_amount or loan.requested_amount)
        schedule = loan.get_amortization_schedule()
        total_interest = sum(r['interest'] for r in schedule)
        total_repayable = amount + total_interest

        terms_text = f"""
        Le prêt accordé est d'un montant de <b>{amount:,.0f} FCFA</b> (
        {self._amount_in_words(amount)}), remboursable sur une période de
        <b>{loan.duration_months} mois</b>, au taux d'intérêt mensuel de
        <b>{float(loan.interest_rate):.2f}%</b> (soit {float(loan.product.annual_interest_rate):.1f}% annuel).
        Le montant total remboursable, intérêts inclus, s'élève à
        <b>{total_repayable:,.0f} FCFA</b>.
        Le remboursement s'effectuera selon un échéancier <b>{loan.product.get_amortization_type_display()}</b>,
        à raison d'une échéance mensuelle.
        """
        elements.append(Paragraph(terms_text, self.body_style))

        if loan.purpose:
            elements.append(Paragraph(
                f"<b>Objet du prêt :</b> {loan.purpose}", self.body_style
            ))

        return elements + [Spacer(1, 0.2 * cm)]

    def _build_amortization_table(self):
        elements = self._section_header("ARTICLE 3 — TABLEAU D'AMORTISSEMENT")

        schedule = self.loan.get_amortization_schedule()

        # Table header
        headers = ['N°', 'Date Échéance', 'Mensualité (FCFA)',
                   'Principal (FCFA)', 'Intérêt (FCFA)', 'Solde Restant (FCFA)']
        data = [headers]

        from dateutil.relativedelta import relativedelta
        start_date = self.loan.first_payment_date or timezone.now().date()

        total_payment = 0
        total_principal = 0
        total_interest = 0

        for i, row in enumerate(schedule):
            due_date = start_date + relativedelta(months=i)
            total_payment += row['payment']
            total_principal += row['principal']
            total_interest += row['interest']
            data.append([
                str(row['installment']),
                due_date.strftime('%d/%m/%Y'),
                f"{row['payment']:,.0f}",
                f"{row['principal']:,.0f}",
                f"{row['interest']:,.0f}",
                f"{row['balance']:,.0f}",
            ])

        # Total row
        data.append([
            'TOTAL', '',
            f"{total_payment:,.0f}",
            f"{total_principal:,.0f}",
            f"{total_interest:,.0f}",
            '',
        ])

        col_widths = [1.2 * cm, 3 * cm, 3.3 * cm, 3.3 * cm, 3.3 * cm, 3.7 * cm]
        table = Table(data, colWidths=col_widths, repeatRows=1)

        style = TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            # Alternating rows
            ('ROWBACKGROUND', (0, 1), (-1, -2),
             [colors.white, TABLE_ALT]),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), BRAND_DARK),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 8),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])
        table.setStyle(style)

        # Show max 24 rows, indicate rest
        if len(schedule) > 24:
            truncated_data = [headers] + data[1:25]
            truncated_data.append(['...', '...', '...', '...', '...', '...'])
            truncated_data.append(data[-1])  # Total
            table = Table(truncated_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(style)
            elements.append(Paragraph(
                f"* Tableau tronqué à 24 mois sur {len(schedule)}. L'échéancier complet vous sera remis.",
                self.small_style
            ))

        return elements + [table, Spacer(1, 0.3 * cm)]

    def _build_clauses(self):
        elements = self._section_header("ARTICLE 4 — CONDITIONS GÉNÉRALES")

        clauses = [
            ("<b>4.1 Remboursement :</b>", "L'emprunteur s'engage à effectuer les remboursements "
             "aux dates prévues dans l'échéancier ci-dessus. Tout retard de paiement entraîne "
             "l'application de pénalités de retard au taux de 2% par mois de retard sur le montant impayé."),
            ("<b>4.2 Utilisation des fonds :</b>",
             f"Les fonds sont destinés exclusivement à : {self.loan.purpose}. "
             "Toute utilisation à d'autres fins constitue une violation du présent contrat."),
            ("<b>4.3 Remboursement anticipé :</b>",
             "L'emprunteur peut procéder à un remboursement anticipé total ou partiel, "
             "après notification de 15 jours à l'établissement. Des frais de remboursement anticipé "
             "de 1% du capital restant dû peuvent s'appliquer."),
            ("<b>4.4 Défaut de paiement :</b>",
             "En cas de non-paiement de 3 échéances consécutives, l'établissement se réserve le droit "
             "de déclarer la totalité du prêt immédiatement exigible et d'engager toutes procédures "
             "de recouvrement légales."),
            ("<b>4.5 Litiges :</b>",
             "Tout litige relatif au présent contrat sera soumis à la juridiction compétente "
             "du lieu du siège social de l'établissement."),
        ]

        for title, content in clauses:
            elements.append(Paragraph(f"{title} {content}", self.body_style))

        return elements + [Spacer(1, 0.3 * cm)]

    def _build_signatures(self):
        elements = self._section_header("ARTICLE 5 — SIGNATURES ET ENGAGEMENTS")

        elements.append(Paragraph(
            "Les parties, après avoir lu et approuvé l'ensemble des clauses du présent contrat, "
            "s'engagent à en respecter scrupuleusement les termes et conditions.",
            self.body_style
        ))
        elements.append(Spacer(1, 0.5 * cm))

        sig_data = [
            ['Pour l\'Établissement', 'L\'Emprunteur', 'Le Garant' if self.loan.guarantor else ''],
            [self.INSTITUTION_NAME, self.client.full_name,
             self.loan.guarantor.full_name if self.loan.guarantor else ''],
            ['', '', ''],
            ['', '', ''],
            ['Signature et cachet', 'Signature', 'Signature' if self.loan.guarantor else ''],
            [f"Fait à Dakar, le {timezone.now().strftime('%d/%m/%Y')}", '', ''],
        ]

        col_count = 3 if self.loan.guarantor else 2
        col_width = 17 * cm / col_count

        t = Table(sig_data[:3 if not self.loan.guarantor else 3],
                  colWidths=[col_width] * col_count)

        sig_table_data = [
            ['Pour l\'Établissement', 'L\'Emprunteur',
             'Le Garant' if self.loan.guarantor else ''],
            [self.INSTITUTION_NAME, self.client.full_name,
             self.loan.guarantor.full_name if self.loan.guarantor else ''],
            [Spacer(1, 2 * cm), Spacer(1, 2 * cm), Spacer(1, 2 * cm)],
            ['_______________________', '_______________________',
             '_______________________' if self.loan.guarantor else ''],
            ['Signature et cachet', 'Signature',
             'Signature' if self.loan.guarantor else ''],
        ]

        sig_table = Table(sig_table_data, colWidths=[5.5 * cm, 5.5 * cm, 6 * cm])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), BRAND_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        elements.append(sig_table)
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
        elements.append(Paragraph(
            f"Document généré automatiquement par {self.INSTITUTION_NAME} — "
            f"Conservez ce document précieusement.",
            self.small_style
        ))
        return elements

    def _info_table_style(self):
        return TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), BRAND_BLUE),
            ('TEXTCOLOR', (2, 0), (2, -1), BRAND_BLUE),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
            ('ROWBACKGROUND', (0, 0), (-1, -1), [LIGHT_GREY, colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ])

    def _amount_in_words(self, amount):
        """Simple amount to words (simplified)"""
        if amount >= 1_000_000:
            return f"{amount/1_000_000:.1f} million(s) de francs CFA"
        elif amount >= 1_000:
            return f"{amount/1_000:.0f} mille francs CFA"
        return f"{amount:.0f} francs CFA"


def generate_loan_contract(loan):
    """Generate and save loan contract PDF"""
    generator = LoanContractGenerator(loan)
    pdf_buffer = generator.generate()

    # Save to media
    output_dir = os.path.join(settings.MEDIA_ROOT, 'contracts')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"contrat_{loan.loan_number}.pdf"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'wb') as f:
        f.write(pdf_buffer.read())

    return filepath, f"contracts/{filename}"
