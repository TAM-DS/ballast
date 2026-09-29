from __future__ import annotations

import re

import gradio as gr

from ballast.engine.risk import score_lane
from ballast.runtime import Ballast
from ballast.schema.models import Brief, RiskRow, Scenario

CSS = """
.gradio-container { max-width: 1600px !important; }
.ballast-header { border-radius: 14px; padding: 22px 26px;
  border: 1px solid #3d6970; background: linear-gradient(120deg, #102c37, #20545a); }
.ballast-header h1 { color: #ffffff !important; letter-spacing: .08em; margin-bottom: 5px; }
.ballast-header p { color: #e2f2ef !important; margin-bottom: 4px; }
.ballast-guide { border-left: 4px solid #d3a24d; border-radius: 8px;
  padding: 10px 14px; background: rgba(55, 132, 130, .12); }
.ballast-guide p { margin: 0; }
"""


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


def scenario_comparison(b: Brief | None, baseline: dict[str, RiskRow]) -> str:
    """Compare exactly the displayed scenario lanes against their engine-scored baseline."""
    if not b or not b.rows:
        return "_No matching lanes to compare. Adjust the tenant or query._"
    shocks = []
    sc = b.scenario
    if sc.extra_delay_days:
        shocks.append(f"+{sc.extra_delay_days:g} days delay")
    if sc.tariff_shock:
        shocks.append(f"{sc.tariff_shock:g}% tariff")
    if sc.port_closed:
        shocks.append(f"Port closure: {sc.port_closed}")
    if sc.typhoon_taiwan:
        shocks.append("Taiwan typhoon overlay")
    title = ", ".join(shocks) if shocks else "No what-if shocks applied"
    lines = [
        f"### Baseline → scenario · {title}",
        "The same deterministic risk engine scores each displayed lane twice: "
        "once without shocks and once using the selected scenario.",
        "",
        "| Lane | Baseline | Scenario | Change | Newly displayed drivers |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in b.rows:
        original = baseline.get(row.lane_id)
        if original is None:
            continue
        change = row.score - original.score
        delta = f"{change:+.1f}" if change else "0.0"
        new_drivers = [d for d in row.drivers if d not in original.drivers]
        drivers = "; ".join(new_drivers) or "No additional displayed drivers"
        lines.append(
            f"| {row.title} | {original.score:.1f} | {row.score:.1f} "
            f"| {delta} | {drivers} |"
        )
    lines.append(
        "\n*Scores are capped at 99. Only lanes matching the current query appear; "
        "this is a scenario comparison, not a forecast or a realized financial outcome.*"
    )
    return "\n".join(lines)


def build_ui() -> gr.Blocks:
    rt = Ballast()
    # Gradio session state keeps each visitor's current decision brief separate.

    with gr.Blocks(title="Ballast", fill_width=True) as demo:
        gr.Markdown(
            "# BALLAST\n"
            "**SUPPLY-CHAIN CONTROL TOWER**  ·  Synthetic scenarios · Human-controlled action\n\n"
            "See which lanes need attention, compare an operational shock against baseline, "
            "and review mitigations without changing bookings or contracts.",
            elem_classes=["ballast-header"],
        )
        gr.Markdown(
            "**WORKFLOW**  01 · Choose a tenant and filter  →  "
            "02 · Score lanes and compare scenarios  →  "
            "03 · Review or explicitly approve a simulated mitigation.",
            elem_classes=["ballast-guide"],
        )
        brief_state = gr.State(value=None)
        labels = rt.tenant_labels()
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 01 · Scope and scenario")
                tenant = gr.Dropdown(choices=labels, value=labels[0] if labels else None, label="Demo tenant")
                query = gr.Textbox(
                    label="Lane filter · supported terms",
                    value="Show me the top 5 risks to semiconductors from Taiwan in the next 30 days",
                )
                delay = gr.Slider(0, 21, value=0, step=1, label="What-if extra delay (days)")
                tariff = gr.Slider(0, 40, value=0, step=5, label="What-if tariff shock (%)")
                port = gr.Textbox(label="What-if port closed", placeholder="Kaohsiung")
                typhoon = gr.Checkbox(label="Typhoon overlay on Taiwan lanes")
                score_btn = gr.Button("Score lanes", variant="primary")
                with gr.Accordion("Local audit trail · expand for decisions", open=False):
                    audit = gr.Textbox(label="Recent audit events", lines=8, interactive=False)
            with gr.Column(scale=2):
                gr.Markdown("### 02 · Risk and scenario impact")
                comparison = gr.Markdown(
                    "_Score lanes to compare the baseline with the selected scenario._"
                )
                with gr.Accordion("Ranked lanes · scores and illustrative exposure", open=True):
                    heat = gr.Markdown()
                with gr.Accordion("Detailed lane brief and action desk", open=False):
                    brief_md = gr.Markdown()
            with gr.Column(scale=1):
                gr.Markdown("### 03 · Decision and controls")
                meta = gr.Textbox(label="Lead lane · heuristic indicators", lines=7, interactive=False)
                pick = gr.Dropdown(
                    label="Proposed mitigation",
                    choices=[],
                    info="Read-only actions can run directly; disruptive proposals require approval.",
                )
                run_btn = gr.Button("Run without approval")
                approve_btn = gr.Button("Approve + simulate", variant="primary")
                deny_btn = gr.Button("Deny selected mitigation")
                result = gr.Textbox(label="Execution decision · simulated outcome", lines=6, interactive=False)
                gr.Markdown(
                    "**Execution boundary:** approval permits a simulated request only. "
                    "No booking, supplier, contract, or purchase order is changed."
                )

        def do_score(label, q, d, t, p, ty):
            sc = Scenario(port_closed=p or "", extra_delay_days=d, tariff_shock=t, typhoon_taiwan=bool(ty))
            brief = rt.run(label, q, sc)
            signals = rt.store.signals(brief.tenant_id)
            baselines = {
                lane.lane_id: score_lane(lane, signals, Scenario())
                for lane in rt.store.lanes(brief.tenant_id)
            }
            lead = brief.rows[0] if brief.rows else None
            meta_txt = (
                f"score: {lead.score}\nseverity: {lead.severity.value}\nusd_at_risk: {lead.usd_at_risk:,.0f}\n"
                f"region: {lead.origin_region}\ncommodity: {lead.commodity}"
                if lead
                else "No matching lanes."
            )
            choices = action_choices(brief)
            return (
                scenario_comparison(brief, baselines),
                heatmap_md(brief),
                format_brief(brief),
                meta_txt,
                gr.update(choices=choices, value=choices[0] if choices else None),
                "\n".join(rt.audit.tail()),
                brief,
            )

        def do_run(choice, brief, approved):
            if not brief:
                return "Score a tenant first.", "\n".join(rt.audit.tail()), brief
            result = rt.execute(brief, action_id(choice), approved)
            return result, "\n".join(rt.audit.tail()), brief

        score_btn.click(
            do_score,
            [tenant, query, delay, tariff, port, typhoon],
            [comparison, heat, brief_md, meta, pick, audit, brief_state],
        )
        run_btn.click(
            lambda c, b: do_run(c, b, False),
            [pick, brief_state],
            [result, audit, brief_state],
        )
        approve_btn.click(
            lambda c, b: do_run(c, b, True),
            [pick, brief_state],
            [result, audit, brief_state],
        )
        deny_btn.click(lambda: "Operator denied. No booking change issued.", outputs=result)

    return demo


def main() -> None:
    demo = build_ui()
    demo.launch(theme=gr.themes.Soft(), css=CSS)


if __name__ == "__main__":
    main()
