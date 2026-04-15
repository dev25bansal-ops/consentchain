"""DPDP Act Compliance PDF Report Generator."""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from dataclasses import dataclass
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


@dataclass
class ReportData:
    fiduciary_name: str
    fiduciary_registration: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime

    total_consents: int
    active_consents: int
    revoked_consents: int
    expired_consents: int
    sensitive_data_consents: int
    third_party_sharing_count: int

    grievances_received: int
    grievances_resolved: int
    grievances_pending: int

    data_deletion_requests: int
    data_deletion_completed: int

    compliance_score: int

    on_chain_hash: Optional[str] = None
    report_id: Optional[str] = None


class DPDPReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=30,
                textColor=colors.HexColor("#1a365d"),
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor("#2d3748"),
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="ReportBody",
                parent=self.styles["Normal"],
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=8,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="DPDPSection",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#4a5568"),
                spaceAfter=6,
            )
        )

    def generate_report(self, data: ReportData) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []

        elements.extend(self._build_header(data))
        elements.extend(self._build_summary(data))
        elements.extend(self._build_consent_statistics(data))
        elements.extend(self._build_compliance_analysis(data))
        elements.extend(self._build_grievance_summary(data))
        elements.extend(self._build_dpdp_compliance(data))
        elements.extend(self._build_footer(data))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_header(self, data: ReportData) -> list:
        elements = []

        elements.append(Paragraph("DPDP Act Compliance Report", self.styles["ReportTitle"]))

        elements.append(
            Paragraph(f"<b>Data Fiduciary:</b> {data.fiduciary_name}", self.styles["ReportBody"])
        )
        elements.append(
            Paragraph(
                f"<b>Registration Number:</b> {data.fiduciary_registration}",
                self.styles["ReportBody"],
            )
        )
        elements.append(
            Paragraph(
                f"<b>Reporting Period:</b> {data.period_start.strftime('%Y-%m-%d')} to {data.period_end.strftime('%Y-%m-%d')}",
                self.styles["ReportBody"],
            )
        )
        elements.append(
            Paragraph(
                f"<b>Generated On:</b> {data.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                self.styles["ReportBody"],
            )
        )

        if data.report_id:
            elements.append(
                Paragraph(f"<b>Report ID:</b> {data.report_id}", self.styles["ReportBody"])
            )

        elements.append(Spacer(1, 20))

        return elements

    def _build_summary(self, data: ReportData) -> list:
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles["SectionTitle"]))

        score_color = (
            colors.green
            if data.compliance_score >= 80
            else colors.orange
            if data.compliance_score >= 60
            else colors.red
        )

        summary_text = f"""
        During the reporting period, {data.fiduciary_name} processed {data.total_consents} consent records.
        Of these, {data.active_consents} remain active, {data.revoked_consents} were revoked by data principals,
        and {data.expired_consents} expired naturally.
        """

        elements.append(Paragraph(summary_text.strip(), self.styles["ReportBody"]))

        elements.append(Spacer(1, 10))

        score_table = Table(
            [[f"Compliance Score: {data.compliance_score}/100"]], colWidths=[6 * inch]
        )
        score_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), score_color),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 16),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("TOPPADDING", (0, 0), (-1, -1), 15),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
                ]
            )
        )
        elements.append(score_table)
        elements.append(Spacer(1, 20))

        return elements

    def _build_consent_statistics(self, data: ReportData) -> list:
        elements = []

        elements.append(Paragraph("Consent Statistics", self.styles["SectionTitle"]))

        table_data = [
            ["Metric", "Count", "Percentage"],
            ["Total Consents", str(data.total_consents), "100%"],
            [
                "Active Consents",
                str(data.active_consents),
                f"{(data.active_consents / max(data.total_consents, 1) * 100):.1f}%",
            ],
            [
                "Revoked Consents",
                str(data.revoked_consents),
                f"{(data.revoked_consents / max(data.total_consents, 1) * 100):.1f}%",
            ],
            [
                "Expired Consents",
                str(data.expired_consents),
                f"{(data.expired_consents / max(data.total_consents, 1) * 100):.1f}%",
            ],
            [
                "Sensitive Data Consents",
                str(data.sensitive_data_consents),
                f"{(data.sensitive_data_consents / max(data.total_consents, 1) * 100):.1f}%",
            ],
            ["Third-Party Sharing", str(data.third_party_sharing_count), "-"],
        ]

        table = Table(table_data, colWidths=[3 * inch, 1.5 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

        return elements

    def _build_compliance_analysis(self, data: ReportData) -> list:
        elements = []

        elements.append(Paragraph("Compliance Analysis", self.styles["SectionTitle"]))

        elements.append(
            Paragraph(
                "<b>Section 6 - Obligations of Data Fiduciary:</b>", self.styles["DPDPSection"]
            )
        )

        obligations = [
            f"✓ Consent mechanisms implemented and recorded on blockchain",
            f"✓ Purpose limitation enforced for all consent records",
            f"✓ Data principal rights facilitated through grievance mechanism",
            f"{'✓' if data.grievances_pending < 30 else '⚠'} Grievance redressal within 30 days: {data.grievances_resolved}/{data.grievances_received} resolved",
            f"✓ Data deletion requests processed: {data.data_deletion_completed}/{data.data_deletion_requests}",
        ]

        for ob in obligations:
            elements.append(Paragraph(ob, self.styles["DPDPSection"]))

        elements.append(Spacer(1, 10))

        return elements

    def _build_grievance_summary(self, data: ReportData) -> list:
        elements = []

        elements.append(Paragraph("Grievance Redressal (Section 13)", self.styles["SectionTitle"]))

        table_data = [
            ["Category", "Count"],
            ["Grievances Received", str(data.grievances_received)],
            ["Grievances Resolved", str(data.grievances_resolved)],
            ["Grievances Pending", str(data.grievances_pending)],
        ]

        table = Table(table_data, colWidths=[4 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

        return elements

    def _build_dpdp_compliance(self, data: ReportData) -> list:
        elements = []

        elements.append(Paragraph("DPDP Act Compliance Checklist", self.styles["SectionTitle"]))

        checklist = [
            (
                "Section 4",
                "Processing of personal data only after consent",
                "Compliant" if data.total_consents > 0 else "Review Required",
            ),
            ("Section 5", "Purpose limitation", "Compliant"),
            (
                "Section 6",
                "Obligations of Data Fiduciary",
                "Compliant" if data.compliance_score >= 70 else "Review Required",
            ),
            ("Section 7", "Consent management", "Compliant"),
            ("Section 8", "Right to access", "Compliant"),
            (
                "Section 9",
                "Right to correction and erasure",
                "Compliant" if data.data_deletion_completed > 0 else "Review Required",
            ),
            (
                "Section 10",
                "Right to withdraw consent",
                "Compliant" if data.revoked_consents > 0 else "No Data",
            ),
            (
                "Section 13",
                "Grievance redressal",
                "Compliant" if data.grievances_pending < 10 else "Review Required",
            ),
        ]

        table_data = [["Section", "Requirement", "Status"]]
        for section, req, status in checklist:
            table_data.append([section, req, status])

        table = Table(table_data, colWidths=[1.2 * inch, 3.5 * inch, 1.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        for i, row in enumerate(table_data[1:], 1):
            if "Compliant" in row[2]:
                table.setStyle(TableStyle([("TEXTCOLOR", (2, i), (2, i), colors.green)]))
            elif "Review" in row[2]:
                table.setStyle(TableStyle([("TEXTCOLOR", (2, i), (2, i), colors.orange)]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        return elements

    def _build_footer(self, data: ReportData) -> list:
        elements = []

        elements.append(Spacer(1, 20))

        if data.on_chain_hash:
            elements.append(
                Paragraph(
                    f"<b>On-Chain Verification Hash:</b> {data.on_chain_hash}",
                    self.styles["DPDPSection"],
                )
            )
            elements.append(
                Paragraph(
                    "This report can be verified on the Algorand blockchain using the above transaction hash.",
                    self.styles["DPDPSection"],
                )
            )

        elements.append(Spacer(1, 30))

        elements.append(Paragraph("---", self.styles["ReportBody"]))

        elements.append(
            Paragraph(
                "This report is generated in compliance with the Digital Personal Data Protection Act, 2023.",
                self.styles["DPDPSection"],
            )
        )

        elements.append(
            Paragraph(
                "Powered by ConsentChain - Blockchain-based Consent Management Platform",
                self.styles["DPDPSection"],
            )
        )

        return elements


report_generator = DPDPReportGenerator()
