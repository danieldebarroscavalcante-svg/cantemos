"""Layout único dos e-mails (estrutura de cartão com cabeçalho, blocos e rodapé em faixa),
nas cores do sistema. E-mail não aceita variáveis CSS: os valores espelham
frontend/styles/tokens.css + app/globals.css."""

from dataclasses import dataclass, field
from html import escape

C = {
    "page": "#000000",  # --bg-base
    "card": "#0B0B0B",  # cartão principal
    "panel": "#141414",  # cartão interno (dados do evento)
    "highlight": "#1C1C1C",  # bloco destacado (cinza escuro)
    "line": "#262626",  # bordas
    "footer": "#070707",  # faixa do rodapé
    "brand": "#FF8A3D",  # --brand
    "on_brand": "#1A0B02",  # --on-brand
    "strong": "#FFFFFF",  # --text-strong
    "text": "#F5F5F5",  # --text-primary
    "muted": "#A3A3A3",  # --text-muted (cinza médio)
    "subtle": "#8A8A8A",  # --text-subtle
    "warn": "#FBBF24",  # selo de prioridade
}
FONT = "'Sora',Arial,Helvetica,sans-serif"
GRADIENT = "linear-gradient(115deg,#FFB37A,#FF8A3D 48%,#F26B1D)"


@dataclass
class InfoRow:
    label: str
    value: str
    mono: bool = False


@dataclass
class TicketCard:
    name: str
    detail: str
    qr_src: str  # "cid:..." no e-mail real, "data:..." na prévia
    priority: bool = False


@dataclass
class EmailParts:
    heading: str
    body: str  # texto já com os campos substituídos (parágrafos separados por linha em branco)
    info_title: str
    info_eyebrow: str = "EVENTO"
    info_rows: list[InfoRow] = field(default_factory=list)
    highlight_label: str | None = None
    highlight_lines: list[str] = field(default_factory=list)
    tickets: list[TicketCard] = field(default_factory=list)
    button_label: str | None = None
    button_url: str | None = None
    footer: str = ""
    logo_src: str | None = None
    logo_alt: str = ""
    brand_text: str = "EVENTMER"


def paragraphs_html(text: str) -> str:
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    return "".join(
        f'<p style="margin:0 0 14px;line-height:1.7;color:{C["muted"]}">'
        + "<br>".join(escape(line) for line in block.split("\n"))
        + "</p>"
        for block in blocks
    )


def paragraphs_text(text: str) -> str:
    return "\n\n".join(b.strip() for b in text.replace("\r\n", "\n").split("\n\n") if b.strip())


def render_html(p: EmailParts) -> str:
    header = (
        f'<img src="{escape(p.logo_src)}" alt="{escape(p.logo_alt)}" '
        f'style="display:block;max-height:56px;max-width:220px">'
        if p.logo_src
        else f'<span style="font-size:13px;font-weight:700;letter-spacing:2px;color:{C["brand"]}">'
        f"{escape(p.brand_text)}</span>"
    )
    rows = "".join(
        f'<p style="margin:10px 0 0;font-size:14px;color:{C["muted"]}">{escape(r.label)}: '
        f'<strong style="color:{C["text"]};'
        + ("font-family:Menlo,Consolas,monospace;letter-spacing:1px;" if r.mono else "")
        + f'">{escape(r.value)}</strong></p>'
        for r in p.info_rows
    )
    highlight = ""
    if p.highlight_label:
        lines = "".join(
            f'<div style="font-size:17px;font-weight:600;color:{C["strong"]};margin-top:4px">{escape(x)}</div>'
            for x in p.highlight_lines
        )
        highlight = (
            f'<div style="margin:16px 0 0;padding:16px 18px;border-radius:10px;background:{C["highlight"]}">'
            f'<div style="font-size:13px;color:{C["muted"]}">{escape(p.highlight_label)}</div>{lines}</div>'
        )
    tickets = ""
    if p.tickets:
        cells = []
        for t in p.tickets:
            badge = (
                f'<div style="display:inline-block;margin-top:8px;padding:3px 10px;border-radius:5px;'
                f'background:{C["highlight"]};color:{C["warn"]};font-size:12px;font-weight:600">'
                "Atendimento prioritário</div>"
                if t.priority
                else ""
            )
            cells.append(
                f'<td style="padding:6px;width:50%;vertical-align:top">'
                f'<div style="background:{C["panel"]};border:1px solid {C["line"]};border-radius:10px;padding:14px;text-align:center">'
                f'<img src="{escape(t.qr_src)}" width="180" height="180" alt="QR Code de {escape(t.name)}" '
                f'style="display:block;margin:0 auto 10px;border-radius:6px;background:#FFFFFF">'
                f'<div style="font-size:16px;font-weight:600;color:{C["text"]}">{escape(t.name)}</div>'
                f'<div style="font-size:13px;color:{C["subtle"]};margin-top:2px">{escape(t.detail)}</div>{badge}</div></td>'
            )
        rows_html = "".join(
            "<tr>" + "".join(cells[i : i + 2]) + "</tr>" for i in range(0, len(cells), 2)
        )
        tickets = (
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin-top:18px">{rows_html}</table>'
        )
    button = (
        f'<p style="margin:24px 0 4px"><a href="{escape(p.button_url)}" style="display:inline-block;'
        f'background:{C["brand"]};background-image:{GRADIENT};color:{C["on_brand"]};text-decoration:none;'
        f'padding:14px 24px;border-radius:9px;font-weight:700;font-size:14px;text-transform:uppercase;'
        f'letter-spacing:0.5px">{escape(p.button_label)}</a></p>'
        if p.button_label and p.button_url
        else ""
    )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark"></head>
<body style="margin:0;padding:24px 12px;background:{C["page"]};font-family:{FONT};color:{C["text"]}">
<div style="max-width:600px;margin:0 auto;background:{C["card"]};border:1px solid {C["line"]};border-top:4px solid {C["brand"]};border-radius:12px;overflow:hidden">
  <div style="padding:22px 28px;border-bottom:1px solid {C["line"]}">{header}</div>
  <div style="padding:26px 28px 8px">
    <h1 style="margin:0 0 16px;font-size:22px;line-height:1.3;font-weight:600;color:{C["strong"]}">{escape(p.heading)}</h1>
    {paragraphs_html(p.body)}
    <div style="margin-top:8px;padding:16px 18px;border:1px solid {C["line"]};border-radius:10px;background:{C["panel"]}">
      <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;color:{C["subtle"]}">{escape(p.info_eyebrow)}</div>
      <div style="margin-top:4px;font-size:17px;font-weight:600;color:{C["strong"]}">{escape(p.info_title)}</div>
      {rows}
    </div>
    {highlight}
    {tickets}
    {button}
  </div>
  <div style="margin-top:22px;padding:16px 28px;background:{C["footer"]};border-top:1px solid {C["line"]};font-size:12px;line-height:1.6;color:{C["subtle"]}">{escape(p.footer)}</div>
</div></body></html>"""


def render_text(p: EmailParts) -> str:
    lines = [p.heading, "", paragraphs_text(p.body), "", p.info_title]
    lines += [f"{r.label}: {r.value}" for r in p.info_rows]
    if p.highlight_label:
        lines += ["", f"{p.highlight_label}:"] + [f"- {x}" for x in p.highlight_lines]
    if p.button_url:
        lines += ["", f"{p.button_label}: {p.button_url}"]
    lines += ["", p.footer]
    return "\n".join(lines).strip() + "\n"
