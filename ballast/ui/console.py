from __future__ import annotations

import re

import gradio as gr

from ballast.runtime import Ballast
from ballast.schema.models import Brief, Scenario

CSS = ".ballast-header {letter-spacing: 0.04em;}"


def format_brief(b: Brief | None) -> str:
    if not b:
        return "_Pick a tenant and click Score lanes._"
    rows = "\n".join(
        f"- **{r.score:.0f}** `{r.severity.value}` {r.title} — ${r.usd_at_risk:,.0f} at risk\n"
        f"  drivers: {'; '.join(r.drivers) or '—'}"
        for r in b.rows
    ) or "- none"
    acts = []
    for r in b.rows:
        for m in r.mitigations:
            gate = "APPROVAL REQUIRED" if m.requires_approval else "read-ok"
            acts.append(f"- `{m.action_id}` **{m.title}** [{gate}] {m.description}")
    tickets = "\n".join(
        f"- `{t['ticket_id']}` p{t['priority']} **{t['title']}** — {t['action']}"
        for t in b.ticket_actions
    ) or "- none"
    return f"""# Ballast brief

{b.narrative}

## Lane risks
{rows}

## Mitigations
{chr(10).join(acts) or '- none'}

## Action desk (tickets)
{tickets}
"""


def action_choices(b: Brief | None) -> list[str]:
    if not b:
        return []
    out = []
    for r in b.rows:
        for m in r.mitigations:
            gate = "APPROVAL" if m.requires_approval else "read"
            out.append(f"{m.title} [{gate}] · {m.action_id}")
    return out


def action_id(choice: str) -> str:
    m = re.search(r"act-[a-z0-9\-]+", choice or "")
    return m.group(0) if m else ""


def heatmap_md(b: Brief | None) -> str:
    if not b or not b.rows:
        return "_No rows._"
    lines = ["| Score | Lane | Region | $ at risk |", "| --- | --- | --- | --- |"]
    for r in b.rows:
        bar = "█" * int(r.score / 10) + "░" * (10 - int(r.score / 10))
        lines.append(f"| {r.score:.0f} {bar} | {r.title} | {r.origin_region} | ${r.usd_at_risk:,.0f} |")
    return "\n".join(lines)


def build_ui() -> gr.Blocks:
    rt = Ballast()
    state = {"brief": None}

    with gr.Blocks(title="Ballast") as demo:
        gr.Markdown(
            "# BALLAST\n"
            "Governed supply-chain risk and scenario planner. "
            "Scores are deterministic. Reroute and dual-source never execute without an approval gate. "
            "Bookings stay untouched."
        )
        labels = rt.tenant_labels()
        with gr.Row():
            with gr.Column(scale=1):
                tenant = gr.Dropdown(choices=labels, value=labels[0] if labels else None, label="Tenant")
                query = gr.Textbox(
                    label="Natural language",
                    value="Show me the top 5 risks to semiconductors from Taiwan in the next 30 days",
                )
                delay = gr.Slider(0, 21, value=0, step=1, label="What-if extra delay (days)")
                tariff = gr.Slider(0, 40, value=0, step=5, label="What-if tariff shock (%)")
                port = gr.Textbox(label="What-if port closed", placeholder="Kaohsiung")
                typhoon = gr.Checkbox(label="Typhoon overlay on Taiwan lanes")
                score_btn = gr.Button("Score lanes", variant="primary")
                audit = gr.Textbox(label="Audit tail", lines=10)
            with gr.Column(scale=2):
                heat = gr.Markdown()
                brief_md = gr.Markdown()
            with gr.Column(scale=1):
                meta = gr.Textbox(label="Lead lane", lines=8)
                pick = gr.Dropdown(label="Mitigation", choices=[])
                run_btn = gr.Button("Run")
                approve_btn = gr.Button("Approve + execute", variant="primary")
                deny_btn = gr.Button("Deny")
                result = gr.Textbox(label="Sandbox result", lines=5)
                gr.Markdown("### Pricing mock\nStarter $0 · Operator $2.4k/mo · Firm $9k/mo + scenario pack")

        def do_score(label, q, d, t, p, ty):
            sc = Scenario(port_closed=p or "", extra_delay_days=d, tariff_shock=t, typhoon_taiwan=bool(ty))
            brief = rt.run(label, q, sc)
            state["brief"] = brief
            lead = brief.rows[0] if brief.rows else None
            meta_txt = (
                f"score: {lead.score}\nseverity: {lead.severity.value}\nusd_at_risk: {lead.usd_at_risk:,.0f}\n"
                f"region: {lead.origin_region}\ncommodity: {lead.commodity}"
                if lead
                else "No matching lanes."
            )
            choices = action_choices(brief)
            return (
                heatmap_md(brief),
                format_brief(brief),
                meta_txt,
                gr.update(choices=choices, value=choices[0] if choices else None),
                "\n".join(rt.audit.tail()),
            )

        def do_run(choice, approved):
            brief = state.get("brief")
            if not brief:
                return "Score a tenant first."
            return rt.execute(brief, action_id(choice), approved)

        score_btn.click(do_score, [tenant, query, delay, tariff, port, typhoon], [heat, brief_md, meta, pick, audit])
        run_btn.click(lambda c: do_run(c, False), [pick], result)
        approve_btn.click(lambda c: do_run(c, True), [pick], result)
        deny_btn.click(lambda: "Operator denied. No booking change issued.", outputs=result)

    return demo


def main() -> None:
    demo = build_ui()
    demo.launch(theme=gr.themes.Soft(), css=CSS)


if __name__ == "__main__":
    main()
