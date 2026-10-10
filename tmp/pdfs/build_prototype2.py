from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


OUT = Path("output/pdf/Veil-Guard-Prototype-2-Submission.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#101B33")
INK = colors.HexColor("#18243B")
MUTED = colors.HexColor("#52627A")
TEAL = colors.HexColor("#087E83")
CYAN = colors.HexColor("#37C9C0")
PALE = colors.HexColor("#EDF6F6")
PAPER = colors.HexColor("#F7F9FC")
LINE = colors.HexColor("#D9E2EC")
AMBER = colors.HexColor("#9A6410")
PALE_AMBER = colors.HexColor("#FFF5E4")
WHITE = colors.white


class SubmissionDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(filename, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                         topMargin=23 * mm, bottomMargin=17 * mm,
                         title="Veil Guard - Prototype 2 Submission",
                         author="Team Astra | Anjuman Institute of Technology and Management")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                      id="main")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=frame, onPage=self.draw_cover),
            PageTemplate(id="content", frames=frame, onPage=self.draw_content),
        ])

    def draw_cover(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.rect(0, 0, 7 * mm, h, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.rect(18 * mm, h - 29 * mm, 26 * mm, 2 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#A8BBCB"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(18 * mm, h - 20 * mm, "ANJUMAN INSTITUTE OF TECHNOLOGY AND MANAGEMENT  /  DATA PRIVACY")
        canvas.setFillColor(colors.HexColor("#8295AD"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(18 * mm, 12 * mm, "TEAM ASTRA  |  PROTOTYPE SUBMISSION 2")
        canvas.drawRightString(w - 17 * mm, 12 * mm, "2026")
        canvas.restoreState()

    def draw_content(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 5 * mm, w, 5 * mm, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.rect(18 * mm, 12 * mm, 10 * mm, 1.2 * mm, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(32 * mm, 11.6 * mm, "VEIL GUARD  /  PROTOTYPE 2")
        canvas.drawRightString(w - 18 * mm, 11.6 * mm, f"{doc.page - 1}  /  3")
        canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", fontName="Helvetica-Bold", fontSize=10,
                          leading=14, textColor=CYAN, spaceAfter=10))
styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=36,
                          leading=41, textColor=WHITE, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", fontName="Helvetica", fontSize=16,
                          leading=23, textColor=colors.HexColor("#CED9E8"), spaceAfter=16))
styles.add(ParagraphStyle(name="CoverBody", fontName="Helvetica", fontSize=11,
                          leading=17, textColor=colors.HexColor("#D8E2EE"), spaceAfter=8))
styles.add(ParagraphStyle(name="PageTitle", fontName="Helvetica-Bold", fontSize=23,
                          leading=28, textColor=NAVY, spaceAfter=5))
styles.add(ParagraphStyle(name="Deck", fontName="Helvetica", fontSize=10,
                          leading=15, textColor=MUTED, spaceAfter=14))
styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=13,
                          leading=17, textColor=NAVY, spaceBefore=7, spaceAfter=6))
styles.add(ParagraphStyle(name="Body2", fontName="Helvetica", fontSize=9.4,
                          leading=14, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=8,
                          leading=11.4, textColor=MUTED))
styles.add(ParagraphStyle(name="SmallWhite", fontName="Helvetica", fontSize=8.5,
                          leading=12.5, textColor=colors.HexColor("#D8E2EE")))
styles.add(ParagraphStyle(name="Label", fontName="Helvetica-Bold", fontSize=8,
                          leading=10, textColor=TEAL, spaceAfter=4))
styles.add(ParagraphStyle(name="Metric", fontName="Helvetica-Bold", fontSize=19,
                          leading=22, textColor=NAVY, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="MetricLabel", fontName="Helvetica-Bold", fontSize=7.5,
                          leading=10, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="FlowNum", fontName="Helvetica-Bold", fontSize=11,
                          leading=14, textColor=WHITE, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="FlowTitle", fontName="Helvetica-Bold", fontSize=9.2,
                          leading=12, textColor=NAVY, spaceAfter=3))
styles.add(ParagraphStyle(name="FlowText", fontName="Helvetica", fontSize=8,
                          leading=11, textColor=INK))
styles.add(ParagraphStyle(name="Callout", fontName="Helvetica-Bold", fontSize=10,
                          leading=15, textColor=NAVY))
styles.add(ParagraphStyle(name="Footnote", fontName="Helvetica", fontSize=7.4,
                          leading=10, textColor=MUTED))


def p(text: str, style="Body2") -> Paragraph:
    return Paragraph(text, styles[style])


def section(text: str) -> Paragraph:
    return p(text, "Section")


def rule_table(data, widths, *, bg=WHITE, grid=LINE, padd=8, repeatRows=0):
    table = Table(data, colWidths=widths, repeatRows=repeatRows, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, grid),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, grid),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padd),
        ("RIGHTPADDING", (0, 0), (-1, -1), padd),
        ("TOPPADDING", (0, 0), (-1, -1), padd),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padd),
    ]))
    return table


story = []

# PAGE 1: Updated proposition and clear change since Prototype 1.
story += [Spacer(1, 39 * mm), p("PROTOTYPE 2  /  PRIVACY MIDDLEWARE FOR AI AGENTS", "CoverKicker"),
          p("VEIL<br/>GUARD", "CoverTitle"),
          p("Protect the tool boundary.<br/>Keep the answer useful.", "CoverSub"),
          Spacer(1, 8 * mm),
          p("AI agents often carry personal values from a user message into a tool request. Veil detects selected patterns locally, replaces matches with reversible task-scoped tokens, verifies the exact outgoing payload, and restores known values on the trusted return path.", "CoverBody"),
          Spacer(1, 8 * mm)]
cover_cards = [[
    p("THE PROBLEM", "Label"), p("THE CHANGE IN PROTOTYPE 2", "Label")
], [
    p("Sensitive values can cross the agent-to-tool boundary and appear in tool logs or responses.", "SmallWhite"),
    p("An end-to-end agent workflow now shows the protected prompt, validated tool proposal, exact local helpdesk receipt, tokenized reply, trusted restoration, and final answer.", "SmallWhite")
]]
cover_table = Table(cover_cards, colWidths=[77 * mm, 77 * mm], rowHeights=[12 * mm, 38 * mm])
cover_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A2945")),
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#3E536E")),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#3E536E")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story += [cover_table, Spacer(1, 12 * mm),
          p("A local-first prototype with an optional networked Gemini agent and a simulated local helpdesk.", "CoverBody"),
          Spacer(1, 11 * mm),
          p("TEAM ASTRA", "CoverKicker"),
          p("Ahmed Ghannam  /  Backend<br/>Muhammed Ibrahim  /  PII detection<br/>Syed Firas  /  Presentation and research", "CoverBody"),
          p("Anjuman Institute of Technology and Management", "SmallWhite"),
          NextPageTemplate("content"), PageBreak()]

# PAGE 2: Architecture / real trust boundaries.
story += [p("One run. One visible trust boundary.", "PageTitle"),
          p("React chat and the six-step workflow page use the same FastAPI run ID and recorded events.", "Deck")]

def flow_row(number, title, detail, tint=WHITE):
    badge = Table([[p(number, "FlowNum")]], colWidths=[11 * mm], rowHeights=[11 * mm])
    badge.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TEAL),
                               ("BOX", (0, 0), (-1, -1), 0, TEAL),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    detail_cell = [p(title, "FlowTitle"), p(detail, "FlowText")]
    row = Table([[badge, detail_cell]], colWidths=[16 * mm, 138 * mm])
    row.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), tint),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 7),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                             ("BOX", (0, 0), (-1, -1), 0.5, LINE)]))
    return row

story += [flow_row("1", "Synthetic ticket intake", "React accepts only a ticket that exists in the local helpdesk. The current seeded ticket is TICKET-DEMO-1042."),
          Spacer(1, 2 * mm), flow_row("2", "Protect model input", "Veil scans locally and tokenizes selected values before an optional Gemini request. The backend, not the browser, holds the provider credential.", PALE),
          Spacer(1, 2 * mm), flow_row("3", "Propose and validate", "Gemini may propose one allowlisted helpdesk lookup. SDK auto-execution is disabled; the application validates the tool name and arguments."),
          Spacer(1, 2 * mm), flow_row("4", "Gate tool egress", "Veil recursively scans the prepared payload, applies task-scoped tokens, and verifies the exact outgoing copy. A residual match blocks dispatch." , PALE),
          Spacer(1, 2 * mm), flow_row("5", "Local simulated helpdesk", "The tool captures the exact protected receipt. Its response may contain tokens; no real external helpdesk is connected."),
          Spacer(1, 2 * mm), flow_row("6", "Restore trusted answer", "Veil checks protected result context before Gemini sees it, restores known tokens locally, and returns the answer to the user.", PALE),
          Spacer(1, 5 * mm)]

fallback = rule_table([
    [p("WHEN GEMINI IS UNAVAILABLE", "Label")],
    [p("Provider errors, connection loss, rejected credentials, exhausted quota, or missing local configuration produce a labeled deterministic fallback in the same run. If the final-answer request fails, fallback reuses the existing tool result and does not call the helpdesk twice.", "Body2")],
], [154 * mm], bg=PALE_AMBER, grid=colors.HexColor("#EBD6AE"), padd=9)
story += [fallback, Spacer(1, 4 * mm),
          p("Trust boundary: the local application owns detection, token mapping, validation, egress checks, and restoration. Gemini is optional and receives protected context. Tokens are reversible pseudonyms, not encryption.", "Footnote"),
          PageBreak()]

# PAGE 3: Reproducible test results with honest caveats.
story += [p("Measured on synthetic data.", "PageTitle"),
          p("Two fixed datasets cover 11 selected entity types. Exact-span scoring and an independent scan of the captured simulated-tool receipt provide separate evidence.", "Deck")]
metric_data = [[p("100%", "Metric"), p("0", "Metric"), p("100%", "Metric"), p("0 calls", "Metric")],
               [p("Held-out recall<br/>26 / 26 planted spans", "MetricLabel"), p("Planted literals<br/>at either receipt", "MetricLabel"), p("Token occurrences<br/>restored", "MetricLabel"), p("Blocked-path<br/>tool dispatches", "MetricLabel")]]
metrics = Table(metric_data, colWidths=[38.5 * mm] * 4, rowHeights=[14 * mm, 15 * mm])
metrics.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WHITE),
                             ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                             ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 5),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                             ("TOPPADDING", (0, 0), (-1, -1), 5),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
story += [metrics, section("Detection and latency"),
          rule_table([
              [p("SPLIT", "Label"), p("CASES / PLANTED", "Label"), p("TP / FP / FN", "Label"), p("PRECISION / RECALL / F2", "Label"), p("P50 / P95", "Label")],
              [p("Development", "Body2"), p("33 / 49", "Body2"), p("49 / 2 / 0", "Body2"), p("96.08% / 100% / 99.19%", "Body2"), p("0.129 / 0.349 ms", "Body2")],
              [p("Held out", "Body2"), p("26 / 26", "Body2"), p("26 / 2 / 0", "Body2"), p("92.86% / 100% / 98.48%", "Body2"), p("0.117 / 0.251 ms", "Body2")],
          ], [24 * mm, 26 * mm, 25 * mm, 48 * mm, 31 * mm], padd=6),
          Spacer(1, 3 * mm),
          p("Latency measures only local gateway sanitization plus egress verification. Each case used 20 warm-ups and 100 timed samples. Gemini, network time, tool execution, and response restoration are excluded. Runtime: Python 3.12.14 on Windows 11 x64. Re-measure on the judging machine.", "Footnote"),
          section("What the test means"),
          p("The benchmark checks selected patterns in synthetic natural-language and nested JSON examples, including repeated values, varied formatting, and benign lookalikes. The held-out set is a fixed repository corpus, not an external or blinded evaluation. Recall is 100% only for the planted examples in these files.", "Body2"),
          p("The two phone false positives in each split came from benign numeric lookalikes. This shows the trade-off of broad phone matching. Detection can miss arbitrary names, unfamiliar formats, misspellings, or obscured values.", "Body2"),
          section("Demo evidence"),
          p("The local demo records the exact payload received by the simulated helpdesk. Independent planted-value scanning found zero exact literals in those receipts. A separate intentional detector-miss path was blocked before dispatch, with zero tool calls and zero receipts. The workflow event stream and evidence page are tied to one run ID.", "Body2"),
          PageBreak()]

# PAGE 4: Scope, honest limits, judging walkthrough, team.
story += [p("Built for a clear, testable demo.", "PageTitle"),
          p("Prototype 2 connects the privacy gateway to an agent workflow and makes the boundary inspectable.", "Deck"),
          section("What is implemented"),
          rule_table([
              [p("COMPONENT", "Label"), p("CURRENT IMPLEMENTATION", "Label")],
              [p("Detection", "Body2"), p("Python recognizers for EMAIL, PHONE_NUMBER, PERSON, STUDENT_ID, AADHAAR, BANK_ACCOUNT, UPI_ID, PAYMENT_CARD, PAN, IFSC, and IBAN.", "Body2")],
              [p("Protection", "Body2"), p("Recursive payload scan, task-scoped reversible token vault, exact egress verification, and fail-closed blocking.", "Body2")],
              [p("Agent and API", "Body2"), p("Deterministic offline agent, optional Gemini adapter, validated tool proposal, FastAPI run snapshots, and replayable SSE events.", "Body2")],
              [p("User interface", "Body2"), p("React chat plus an animated six-step CSS/SVG and Motion trace for the same run. Streamlit remains a deterministic fallback and includes a nested JSON example.", "Body2")],
              [p("Tool", "Body2"), p("Local simulated helpdesk with a single seeded ticket, TICKET-DEMO-1042. No production system or real support data is connected.", "Body2")],
          ], [35 * mm, 119 * mm], padd=7),
          section("How to show it"),
          p("1. Start the FastAPI backend and React frontend.  2. Submit a fictional request naming TICKET-DEMO-1042.  3. Open the same run's workflow link.  4. Point to the tokenized prompt when Gemini succeeds, or the labeled local fallback when it is unavailable.  5. Show Veil's egress result, the exact protected helpdesk receipt, tokenized tool response, restored response, and final answer.", "Body2"),
          section("Limits and next work"),
          p("This is a selected-pattern prototype, not universal PII detection. Tokens are reversible pseudonyms held in a task-scoped in-memory vault; they are not encryption or production key management. The simulated helpdesk is local. Gemini makes an external request with protected synthetic context, but a fresh successful live Gemini browser run has not been verified for this submission. Focused Python and frontend checks pass; the full Python suite stalled in a Windows AppTest environment and is not claimed as passing.", "Body2"),
          p("Next work: broader and independently reviewed benchmarks, stronger person-name recognition, production-grade vault/session design, and live verification on the judging machine.", "Body2"),
          Spacer(1, 4 * mm)]

end = rule_table([
    [p("TEAM ASTRA", "Label")],
    [p("Ahmed Ghannam - Backend   |   Muhammed Ibrahim - PII detection   |   Syed Firas - Presentation and research", "Body2")],
    [p("Anjuman Institute of Technology and Management", "Small")],
], [154 * mm], bg=WHITE, padd=8)
story.append(end)

doc = SubmissionDoc(str(OUT))
doc.build(story)
print(OUT.resolve())
