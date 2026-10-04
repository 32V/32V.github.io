#!/usr/bin/env python3
"""Build the downloadable CV from assets/json/resume.json.

Install requirements.txt, then run: python bin/build_cv.py
Use --output to preview the PDF without replacing the published asset.
"""

import argparse
import json
from datetime import date, datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
LINK_COLOR = "#17458a"


def register_fonts():
    """Embed a serif font with Greek glyphs on macOS or Linux."""
    candidates = [
        (Path("/System/Library/Fonts/Supplemental"), "Times New Roman"),
        (Path("/usr/share/fonts/truetype/liberation2"), "LiberationSerif"),
        (Path("/usr/share/fonts/truetype/liberation"), "LiberationSerif"),
        (Path("/usr/share/fonts/truetype/dejavu"), "DejaVuSerif"),
    ]
    for directory, base in candidates:
        if base == "Times New Roman":
            files = [f"{base}{suffix}.ttf" for suffix in ("", " Bold", " Italic", " Bold Italic")]
        elif base == "DejaVuSerif":
            files = [f"{base}{suffix}.ttf" for suffix in ("", "-Bold", "-Italic", "-BoldItalic")]
        else:
            files = [f"{base}-{suffix}.ttf" for suffix in ("Regular", "Bold", "Italic", "BoldItalic")]
        if all((directory / filename).is_file() for filename in files):
            for name, filename in zip(("CV", "CV-Bold", "CV-Italic", "CV-BoldItalic"), files):
                pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
            pdfmetrics.registerFontFamily("CV", normal="CV", bold="CV-Bold", italic="CV-Italic", boldItalic="CV-BoldItalic")
            return "CV"
    return "Times-Roman"


def text(value):
    return escape(str(value).replace("–", "-").replace("—", "-"))


def link(label, url):
    return f'<a href="{escape(url, quote=True)}" color="{LINK_COLOR}">{text(label)}</a>'


def format_date(value):
    if len(value) == 7 and value[4] == "-":
        return datetime.strptime(value, "%Y-%m").strftime("%b. %Y")
    if len(value) == 10 and value[4] == "-":
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b. %Y")
    return value.replace("–", "-")


def date_range(entry):
    return f"{format_date(entry['startDate'])} - {format_date(entry['endDate']) if entry.get('endDate') else 'Present'}"


def build(output, updated):
    resume = json.loads((ROOT / "assets/json/resume.json").read_text())
    font = register_fonts()
    body = ParagraphStyle("Body", fontName=font, fontSize=10.8, leading=12.7)
    small = ParagraphStyle("Small", parent=body, fontSize=9.5, leading=11.5)
    right = ParagraphStyle("Right", parent=body, alignment=TA_RIGHT)
    heading = ParagraphStyle("Heading", parent=body, fontSize=13.5, leading=16, spaceBefore=10, keepWithNext=True)
    name = ParagraphStyle("Name", parent=body, fontSize=23, leading=27, alignment=TA_CENTER)
    contact = ParagraphStyle("Contact", parent=body, alignment=TA_CENTER, spaceAfter=4)
    width = A4[0] - 64
    story = []

    def p(content, style=body):
        return Paragraph(content, style)

    def section(title):
        story.extend([p(title.upper(), heading), HRFlowable(width="100%", thickness=0.5, color=colors.black), Spacer(1, 4)])

    def row(left, right_text, left_width=None):
        left_width = left_width or width - 145
        table = Table([[p(left), p(text(right_text), right)]], colWidths=[left_width, width - left_width])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        return table

    basics = resume["basics"]
    story.append(p(text(basics["name"]), name))
    profiles = {profile["network"]: profile for profile in basics["profiles"]}
    contacts = [link("32V", profiles["GitHub"]["url"]), link("LinkedIn", profiles["LinkedIn"]["url"]), link("Website", basics["url"]), link(basics["email"], "mailto:" + basics["email"])]
    story.append(p(" | ".join(contacts), contact))

    section("Academic Interests")
    story.append(p(text(", ".join(keyword for item in resume["interests"] for keyword in item["keywords"]))))

    section("Education")
    for entry in resume["education"]:
        block = [row(link("Korea Advanced Institute of Science and Technology (KAIST)", entry["url"]), date_range(entry), width - 130), p(text(f"{entry['studyType']} in {entry['area']}"))]
        block.extend(p(text(course)) for course in entry.get("courses", []))
        block.append(Spacer(1, 5))
        story.append(KeepTogether(block))

    section("Research Experience")
    for entry in resume["work"]:
        # The current M.S. appointment is already listed under Education.
        if entry["position"] == "M.S. Student":
            continue
        story.append(KeepTogether([row(link(entry["name"], entry["url"]), date_range(entry)), p(text(entry["position"]) + " - Advisor: " + link("Minhyuk Sung", "https://mhsung.github.io/"))]))

    section("Publications")
    for number, entry in enumerate(resume["publications"], 1):
        authors = text(entry["authors"]).replace(text(basics["name"]), "<b>" + text(basics["name"]) + "</b>").replace("*", "<super>*</super>")
        paper_style = ParagraphStyle(f"Paper{number}", parent=body, leftIndent=15, firstLineIndent=-15)
        details_style = ParagraphStyle(f"Details{number}", parent=body, leftIndent=15)
        title = entry["name"]
        if font == "Times-Roman":
            # Standard PDF Times lacks Greek; Symbol supplies the Psi glyph.
            title_markup = link(title.replace("Ψ", "PSI_GLYPH"), entry["url"]).replace("PSI_GLYPH", '<font name="Symbol">Y</font>')
        else:
            title_markup = link(title, entry["url"])
        story.append(KeepTogether([p(f"{number}. {title_markup}", paper_style), p(authors, details_style), p("<i>" + text(entry["publisher"]) + "</i>", details_style), Spacer(1, 5)]))
    story.append(p("* Equal contribution.", small))

    story.append(PageBreak())
    section("Teaching")
    for entry in resume["teaching"]:
        story.extend([row("<b>" + text(entry["position"]) + "</b>, " + text(entry["organization"]), entry["date"], width - 110), p(link(entry["name"], entry["url"])), p(text(entry["summary"])), Spacer(1, 4)])

    section("Talks")
    for entry in resume["talks"]:
        story.extend([row("<b>" + text(entry["position"]) + "</b>", entry["date"]), p(link(entry["name"], entry["url"])), p(text(entry["organization"])), Spacer(1, 4)])

    section("Honors and Awards")
    for entry in resume["awards"]:
        title = link(entry["title"], entry["url"]) if entry.get("url") else text(entry["title"])
        details = text(entry["awarder"])
        if entry.get("summary"):
            details += " - " + text(entry["summary"])
        story.append(KeepTogether([row(title, format_date(entry["date"]), width - 70), p(details), Spacer(1, 7)]))

    section("Academic Service")
    for entry in resume["volunteer"]:
        story.append(row(text(entry["position"]) + ", " + link(entry["organization"], entry["url"]), entry["startDate"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8.5)
        canvas.setFillColor(colors.HexColor("#606060"))
        canvas.drawString(32, 22, f"Last updated: {updated.strftime('%B %d, %Y')}")
        canvas.drawRightString(A4[0] - 32, 22, str(doc.page))
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=32, leftMargin=32, topMargin=28, bottomMargin=36, title=basics["name"] + " - Curriculum Vitae", author=basics["name"])
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "assets/pdf/CV.pdf")
    parser.add_argument("--updated", type=date.fromisoformat, default=date.today(), help="Last-updated date in YYYY-MM-DD format")
    args = parser.parse_args()
    build(args.output, args.updated)
    print(args.output)
