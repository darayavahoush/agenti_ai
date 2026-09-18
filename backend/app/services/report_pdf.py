"""
services/report_pdf.py — ICF-style progress report, rendered to PDF.

Pulls from the same aggregates the dashboard already computes (PatientProgress,
weekly summary, goals, assignments, and — when passed in — the cross-game
phoneme summary) rather than re-querying the DB, so the PDF can never drift
out of sync with what the therapist sees on screen.

Visual design mirrors the app's own brand palette (frontend/tailwind.config.js
`brand.*`): a colored cover band, small KPI cards, and color-coded severity
badges, rather than a plain black-and-white table dump.
"""

from datetime import datetime, timezone

# reportlab is imported lazily (inside build_patient_report_pdf) rather than
# at module load time. If reportlab is ever missing or fails to install, this
# module can still be imported cleanly — only the PDF-export endpoint itself
# fails, not the entire app's startup. See PDF_EXPORT_UNAVAILABLE below.
_styles = _h1 = _h2 = _body = _small = None
PDF_EXPORT_UNAVAILABLE = None  # set to the ImportError string if unavailable

# Brand palette, matching frontend/tailwind.config.js `brand.*` exactly, so
# the PDF a therapist downloads looks like it came from the same product as
# the dashboard they're looking at.
_BRAND = {
    "green":  "#A8FF6F",
    "teal":   "#1D9E75",
    "coral":  "#E24B4A",
    "amber":  "#FAC775",
    "purple": "#7850DC",
    "dark":   "#12122A",
    "card":   "#1E1E3F",
}

_COVER_BAND_HEIGHT = 1.15  # inches
_FOOTER_ZONE = 0.5  # inches

# Brand identity, matching the live site (frontend/index.html <title>,
# README.md, app/config.py's API_BASE_URL) -- previously the PDF never
# named the product or where it lives, so a page forwarded on its own read
# as an anonymous clinical export rather than something from Vaaksudhi.
_BRAND_NAME = "Vaaksudhi"
_SITE_URL = "vaaksudhi.manaslearning.com"


def _init_styles():
    global _styles, _h1, _h2, _body, _small, PDF_EXPORT_UNAVAILABLE
    if _styles is not None or PDF_EXPORT_UNAVAILABLE is not None:
        return
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        _styles = getSampleStyleSheet()
        _h1 = _styles["Title"]
        _h2 = ParagraphStyle("h2", parent=_styles["Heading2"], spaceBefore=14, spaceAfter=6,
                              textColor=colors.HexColor(_BRAND["dark"]))
        _body = _styles["Normal"]
        _small = ParagraphStyle("small", parent=_styles["Normal"], fontSize=9, textColor=colors.grey)
    except ImportError as e:
        PDF_EXPORT_UNAVAILABLE = str(e)


def _fmt_date(d):
    if not d:
        return "—"
    if isinstance(d, str):
        return d[:10]
    return d.strftime("%b %d, %Y")


# ICF-style qualifier scale (0 = no difficulty ... 4 = complete difficulty),
# collapsed to 4 rule-based bands driven by in-app performance data. This is
# NOT a clinical severity diagnosis — it's a practice-performance indicator a
# therapist reads alongside their own assessment, and the report says so
# explicitly wherever it appears.
def _severity_band(rate):
    """rate: 0..1 or None. Returns (label, ICF-style qualifier, brand color key)."""
    if rate is None:
        return ("Not yet assessed", "—", None)
    if rate >= 0.80:
        return ("No/mild difficulty", "0–1", "teal")
    if rate >= 0.60:
        return ("Mild difficulty", "1", "amber")
    if rate >= 0.40:
        return ("Moderate difficulty", "2", "coral")
    return ("Severe difficulty", "3", "coral")


def _make_numbered_canvas(patient_first_name, generated_on):
    """Returns a Canvas subclass that draws the cover band on page 1 and a
    footer with accurate "Page X of Y" on every page. Deferred page counting
    needs a canvas subclass (reportlab's standard pattern) since the total
    page count isn't known until the whole story has been laid out."""
    from reportlab.pdfgen import canvas as canvas_mod
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter

    page_w, page_h = letter
    band_h = _COVER_BAND_HEIGHT * 72
    footer_h = _FOOTER_ZONE * 72

    class _ReportCanvas(canvas_mod.Canvas):
        def __init__(self, *args, **kwargs):
            canvas_mod.Canvas.__init__(self, *args, **kwargs)
            self._saved_pages = []

        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_pages)
            for i, state in enumerate(self._saved_pages, start=1):
                self.__dict__.update(state)
                self._draw_chrome(i, total)
                canvas_mod.Canvas.showPage(self)
            canvas_mod.Canvas.save(self)

        def _draw_chrome(self, page_num, total_pages):
            self.saveState()
            if page_num == 1:
                self.setFillColor(colors.HexColor(_BRAND["dark"]))
                self.rect(0, page_h - band_h, page_w, band_h, stroke=0, fill=1)
                self.setFillColor(colors.HexColor(_BRAND["green"]))
                self.rect(0, page_h - band_h, page_w, 4, stroke=0, fill=1)

                # Brand mark, top-right of the band: a small two-tone dot
                # (echoes the app's own sparkle/orb accents) plus a
                # letter-spaced wordmark. Previously the band had no brand
                # identity at all -- just the generic title -- so a
                # therapist (or a parent it got forwarded to) had no visual
                # cue this came from Vaaksudhi rather than a plain export.
                self.setFont("Helvetica-Bold", 9)
                wordmark = " ".join(_BRAND_NAME.upper())  # reportlab has no letter-tracking API
                wordmark_w = self.stringWidth(wordmark, "Helvetica-Bold", 9)
                wm_x = page_w - 0.75 * 72 - wordmark_w
                wm_y = page_h - 0.34 * 72
                dot_cx = wm_x - 10
                self.setFillColor(colors.HexColor(_BRAND["green"]))
                self.circle(dot_cx, wm_y + 3, 4, stroke=0, fill=1)
                self.setFillColor(colors.HexColor(_BRAND["dark"]))
                self.circle(dot_cx + 1.5, wm_y + 1.5, 1.8, stroke=0, fill=1)
                self.setFillColor(colors.white)
                self.drawString(wm_x, wm_y, wordmark)

                self.setFillColor(colors.white)
                self.setFont("Helvetica-Bold", 20)
                self.drawString(0.75 * 72, page_h - 0.6 * 72,
                                 f"Progress Report — {patient_first_name}")
                self.setFillColor(colors.HexColor(_BRAND["green"]))
                self.setFont("Helvetica", 9)
                self.drawString(0.75 * 72, page_h - 0.9 * 72,
                                 f"Generated {generated_on}  ·  {_SITE_URL}")

            self.setStrokeColor(colors.lightgrey)
            self.setLineWidth(0.4)
            self.line(0.75 * 72, footer_h, page_w - 0.75 * 72, footer_h)
            self.setFillColor(colors.grey)
            self.setFont("Helvetica", 8)
            self.drawString(0.75 * 72, footer_h - 12,
                             "Practice-performance data from in-app activity — not a substitute for clinical assessment.")
            self.drawRightString(page_w - 0.75 * 72, footer_h - 12,
                                  f"Page {page_num} of {total_pages}")
            # Brand + site, every page -- not just the cover -- so a page
            # separated from page 1 (printed loose, forwarded as a single
            # attachment) still traces back to Vaaksudhi.
            self.setFont("Helvetica", 7)
            self.setFillColor(colors.HexColor(_BRAND["purple"]))
            self.drawString(0.75 * 72, footer_h - 22, f"{_BRAND_NAME} · {_SITE_URL}")
            self.restoreState()

    return _ReportCanvas


def _kpi_card(label, value, color_key, colors, Paragraph, ParagraphStyle, Table, TableStyle, inch):
    num_style = ParagraphStyle(
        f"kpi_num_{label}", fontName="Helvetica-Bold", fontSize=18,
        textColor=colors.white, alignment=1, spaceAfter=2,
    )
    label_style = ParagraphStyle(
        f"kpi_label_{label}", fontName="Helvetica", fontSize=8,
        textColor=colors.HexColor(_BRAND["green"]) if color_key == "dark" else colors.white,
        alignment=1,
    )
    cell = Table(
        [[Paragraph(str(value), num_style)], [Paragraph(label, label_style)]],
        colWidths=[1.35 * inch],
    )
    cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_BRAND[color_key])),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return cell


def _severity_badge_cell(label, color_key, colors, Paragraph, ParagraphStyle, Table, TableStyle):
    if color_key is None:
        bg, fg = colors.lightgrey, colors.grey
    else:
        bg = colors.HexColor(_BRAND[color_key])
        fg = colors.white if color_key in ("coral", "teal", "purple") else colors.HexColor(_BRAND["dark"])
    style = ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=8, textColor=fg, alignment=1)
    t = Table([[Paragraph(label, style)]], colWidths=[1.6 * 72], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def build_patient_report_pdf(
    *, patient, progress, weekly_summary, goals, assignments, therapist,
    output_path: str, goal_histories: dict | None = None,
    phoneme_summary=None,
) -> str:
    """
    patient:          Patient ORM object
    progress:         PatientProgress (pydantic) — from get_patient_progress
    weekly_summary:   WeeklySummaryOut (pydantic) — from generate_weekly_summary
    goals:            list[GoalOut]
    assignments:      list[AssignmentOut]
    therapist:        Therapist ORM object
    output_path:      where to write the PDF
    phoneme_summary:  optional CrossGamePhonemeSummaryOut (pydantic) or dict —
                       from services/phoneme_summary.get_cross_game_phoneme_summary.
                       Section is skipped entirely if not provided or empty.
    """
    _init_styles()
    if PDF_EXPORT_UNAVAILABLE:
        raise RuntimeError(f"PDF export is temporarily unavailable: {PDF_EXPORT_UNAVAILABLE}")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    from reportlab.lib.styles import ParagraphStyle

    now = datetime.now(timezone.utc)
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=_COVER_BAND_HEIGHT * inch + 0.35 * inch, bottomMargin=_FOOTER_ZONE * inch + 0.3 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    story = []

    # --- Prepared-by line (title itself now lives in the cover band) ---
    story.append(Paragraph(
        f"Prepared by {therapist.full_name}"
        + (f", {therapist.clinic_name}" if therapist.clinic_name else ""),
        _small,
    ))
    story.append(Spacer(1, 10))

    # --- KPI card row (ICF: quick-glance activity summary) ---
    kpi_cells = [
        _kpi_card("Sessions", progress.total_sessions, "purple",
                  colors, Paragraph, ParagraphStyle, Table, TableStyle, inch),
        _kpi_card("Stars", f"{progress.total_stars}/{progress.max_possible_stars}", "teal",
                  colors, Paragraph, ParagraphStyle, Table, TableStyle, inch),
        _kpi_card("Completion", f"{progress.completion_rate * 100:.0f}%", "coral",
                  colors, Paragraph, ParagraphStyle, Table, TableStyle, inch),
        _kpi_card(
            "Trend (5v5)",
            (f"{'+' if progress.improvement_trend >= 0 else ''}{progress.improvement_trend}"
             if progress.improvement_trend is not None else "—"),
            "dark", colors, Paragraph, ParagraphStyle, Table, TableStyle, inch,
        ),
    ]
    kpi_row = Table([kpi_cells], colWidths=[1.45 * inch] * 4, hAlign="LEFT")
    kpi_row.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(kpi_row)
    story.append(Spacer(1, 16))

    # --- Client info (ICF: personal/contextual factors) ---
    story.append(Paragraph("Client Information", _h2))
    info_rows = [
        ["Name", patient.first_name],
        ["Age", str(patient.age) if patient.age is not None else "—"],
        ["Diagnosis / notes", patient.diagnosis_notes or "—"],
    ]
    t = Table(info_rows, colWidths=[1.5 * inch, 4.5 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # --- Severity indicators (ICF: body function qualifiers) ---
    story.append(Paragraph("Practice Performance Severity Indicators", _h2))
    story.append(Paragraph(
        "Rule-based, derived from in-app practice data only — not a clinical "
        "severity diagnosis. Use alongside your own standardized assessment.",
        _small,
    ))
    story.append(Spacer(1, 4))

    goal_rate = (
        sum(1 for g in goals if g.achieved) / len(goals) if goals else None
    )
    severity_header = ["Domain", "Performance", "Severity band", "ICF qualifier"]
    severity_data_rows = []
    for domain, rate in [
        ("BreathQuest (completion rate)", progress.completion_rate),
        ("Goals (achievement rate)", goal_rate),
    ]:
        label, qualifier, color_key = _severity_band(rate)
        severity_data_rows.append((
            domain,
            f"{rate * 100:.0f}%" if rate is not None else "No data",
            label, qualifier, color_key,
        ))
    severity_rows = [severity_header] + [
        [domain, perf, _severity_badge_cell(label, color_key, colors, Paragraph, ParagraphStyle, Table, TableStyle), qual]
        for domain, perf, label, qual, color_key in severity_data_rows
    ]
    t = Table(severity_rows, colWidths=[2.3 * inch, 1.3 * inch, 1.6 * inch, 1.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (2, 1), (2, -1), 0),
        ("RIGHTPADDING", (2, 1), (2, -1), 0),
        ("TOPPADDING", (2, 1), (2, -1), 0),
        ("BOTTOMPADDING", (2, 1), (2, -1), 0),
    ]))
    story.append(t)

    # --- Per-level breakdown ---
    story.append(Paragraph("Per-Level Breakdown", _h2))
    level_header = ["Level", "Attempts", "Best ★", "Avg ★", "Avg Breath", "Last Played"]
    level_rows = [level_header] + [
        [
            lp.level_name, str(lp.attempts), str(lp.best_stars), f"{lp.avg_stars:.2f}",
            f"{lp.avg_breath_strength:.2f}" if lp.avg_breath_strength else "—",
            _fmt_date(lp.last_played),
        ]
        for lp in progress.level_progress
    ]
    t = Table(level_rows, colWidths=[1.5 * inch, 0.8 * inch, 0.6 * inch, 0.6 * inch, 0.9 * inch, 1.1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)

    # --- Cross-game phoneme summary (ICF: body function detail behind the
    # activity summary above — same data as the dashboard's "Phoneme Command
    # Center" card, so the printed report and the on-screen view never disagree) ---
    if phoneme_summary is not None:
        ps = phoneme_summary if isinstance(phoneme_summary, dict) else phoneme_summary.model_dump()
        if ps.get("phonemes"):
            story.append(Paragraph("Cross-Game Phoneme Summary", _h2))
            story.append(Paragraph(
                f"Merged across Flashcards, VaakMirror, and Chime — "
                f"{ps['total_attempts']} total attempts, "
                f"{ps['overall_accuracy'] * 100:.0f}% overall accuracy.",
                _small,
            ))
            story.append(Spacer(1, 4))

            if ps.get("game_totals"):
                game_labels = {"flashcards": "Flashcards", "vaakmirror": "VaakMirror", "chime": "Chime"}
                game_header = ["Game", "Attempts", "Accuracy"]
                game_rows = [game_header]
                for g in ps["game_totals"]:
                    _, _, color_key = _severity_band(g["accuracy"])
                    game_rows.append([
                        game_labels.get(g["game"], g["game"]), str(g["attempts"]),
                        _severity_badge_cell(f"{g['accuracy'] * 100:.0f}%", color_key,
                                              colors, Paragraph, ParagraphStyle, Table, TableStyle),
                    ])
                t = Table(game_rows, colWidths=[2.5 * inch, 1.2 * inch, 1.6 * inch])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (2, 1), (2, -1), 0),
                    ("RIGHTPADDING", (2, 1), (2, -1), 0),
                    ("TOPPADDING", (2, 1), (2, -1), 0),
                    ("BOTTOMPADDING", (2, 1), (2, -1), 0),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))

            if ps.get("by_category"):
                cat_header = ["Category", "Attempts", "Accuracy"]
                cat_rows = [cat_header]
                for c in ps["by_category"]:
                    label, _, color_key = _severity_band(c["accuracy"])
                    cat_rows.append([
                        c["category"].title(), str(c["attempts"]),
                        _severity_badge_cell(f"{c['accuracy'] * 100:.0f}%", color_key,
                                              colors, Paragraph, ParagraphStyle, Table, TableStyle),
                    ])
                t = Table(cat_rows, colWidths=[2.5 * inch, 1.2 * inch, 1.6 * inch])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (2, 1), (2, -1), 0),
                    ("RIGHTPADDING", (2, 1), (2, -1), 0),
                    ("TOPPADDING", (2, 1), (2, -1), 0),
                    ("BOTTOMPADDING", (2, 1), (2, -1), 0),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))

            if ps.get("weakest"):
                story.append(Paragraph("Priority Focus (weakest phonemes)", ParagraphStyle(
                    "weakestHeading", parent=_body, fontName="Helvetica-Bold", fontSize=10, spaceAfter=4,
                )))
                weak_header = ["Phoneme", "Example", "Attempts", "Accuracy"]
                weak_rows = [weak_header] + [
                    [w["phoneme"], w.get("example_word") or "—", str(w["attempts"]), f"{w['accuracy'] * 100:.0f}%"]
                    for w in ps["weakest"][:5]
                ]
                t = Table(weak_rows, colWidths=[1.2 * inch, 1.6 * inch, 1.0 * inch, 1.0 * inch])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_BRAND["coral"])),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                story.append(t)

    # --- Goals (ICF: activity/participation targets) ---
    story.append(Paragraph("Goals", _h2))
    if goals:
        goal_header = ["Target", "Baseline", "Current", "Target Value", "Target Date", "Status"]
        goal_rows = [goal_header] + [
            [
                g.target_metric,
                f"{g.baseline_value:.2f}" if g.baseline_value is not None else "—",
                f"{g.current_value:.2f}" if g.current_value is not None else "—",
                f"{g.target_value:.2f}",
                _fmt_date(g.target_date),
                "Achieved" if g.achieved else "In progress",
            ]
            for g in goals
        ]
        t = Table(goal_rows, colWidths=[1.4 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch, 1.0 * inch, 0.9 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No goals set yet.", _body))

    # --- Assignments / homework ---
    story.append(Paragraph("Homework Assignments", _h2))
    if assignments:
        a_header = ["Title", "Game", "Status", "Due"]
        a_rows = [a_header] + [
            [a.title, a.game, a.status.value if hasattr(a.status, "value") else a.status, _fmt_date(a.due_at)]
            for a in assignments[:10]
        ]
        t = Table(a_rows, colWidths=[2.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No assignments yet.", _body))

    # --- Weekly narrative (most recent week, plain-language) ---
    story.append(PageBreak())
    story.append(Paragraph("This Week — Narrative Summary", _h2))
    story.append(Paragraph(weekly_summary.narrative, _body))
    story.append(Spacer(1, 8))
    if weekly_summary.highlights:
        for h in weekly_summary.highlights:
            story.append(Paragraph(f"• {h}", _body))

    # --- Appendix: per-goal session history (raw values behind the goal's
    # current_value rolling average, same series the Care tab expands to show) ---
    if goal_histories and any(goal_histories.values()):
        story.append(PageBreak())
        story.append(Paragraph("Appendix — Goal History", _h2))
        story.append(Paragraph(
            "Session-by-session values behind each goal's current progress figure.",
            _small,
        ))
        story.append(Spacer(1, 6))
        for g in goals:
            entries = goal_histories.get(g.id) or []
            if not entries:
                continue
            story.append(Paragraph(g.target_metric, ParagraphStyle(
                "goalHistHeading", parent=_body, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4,
            )))
            hist_header = ["Date", "Value"]
            hist_rows = [hist_header] + [
                [_fmt_date(e.date), e.label] for e in entries
            ]
            t = Table(hist_rows, colWidths=[2.0 * inch, 1.5 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ]))
            story.append(t)
            story.append(Spacer(1, 4))

    canvasmaker = _make_numbered_canvas(patient.first_name, _fmt_date(now))
    doc.build(story, canvasmaker=canvasmaker)
    return output_path
