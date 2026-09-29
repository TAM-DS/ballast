# BALLAST | Governed Supply-Chain Risk & Scenario Planning

**See the disruption. Model the options. Keep operational decisions under human control.**

BALLAST is a runnable, multi-tenant supply-chain risk prototype for operations leaders and the teams responding to disruption. It ranks synthetic shipping lanes using an explainable, deterministic scoring model, lets operators apply what-if shocks, connects lane risk to an action desk, and proposes mitigations **without silently changing bookings or contracts**.

> **A risk score is not a decision. A recommendation is not permission to reroute.**

[Explore the demo](#run-it-locally) · [See the control boundary](#the-decision-boundary) · [Inspect the architecture](#architecture)

This is the operations-domain counterpart to [AEGIS Analyst](https://github.com/TAM-DS/aegis-analyst): a different business problem, but the same deliberate separation between analysis, authorization, and execution.

---

## The business moment: the risk is real; the reroute is not automatic

Imagine two operations teams working through disruptions:

- A semiconductor manufacturer depends on Taiwan-origin shipments. Concentration, single-source exposure, and a potential typhoon threaten deliveries to U.S. facilities.
- An energy trading desk evaluates crude movements through the Gulf while a synthetic Hormuz-adjacent chokepoint alert raises concern about the route.

A dashboard can flag both problems. The harder question is **what the organization should do next—and who is allowed to make that change**.

BALLAST turns the relevant synthetic lanes and signals into ranked risk briefs. The operator can model additional delay, a tariff shock, a port closure, or a Taiwan typhoon overlay, then compare baseline and shocked risk scores for the displayed lanes before inspecting proposed mitigations.

When the operator selects a disruptive mitigation such as **Reroute active POs** or **Open dual-source RFQ** and clicks **Run** without approval, the policy gate responds:

```text
DENIED: approval required for Reroute active POs
```

After **Approve + execute**, the runtime produces a simulated queueing result:

```text
[SIMULATED] Reroute active POs queued for <action-id>.
Bookings and contracts unchanged until ops confirms.
```

**That distinction is the product demonstration:** BALLAST helps operators evaluate and authorize a response. It does not claim that a shipment moved, a supplier accepted an RFQ, or a contract changed.

## The decision boundary

| Step | What BALLAST does | What it does not do |
| --- | --- | --- |
| **Assess** | Scores tenant-specific lanes and exposes the main risk drivers. | Claim to predict disruptions using a trained forecasting model. |
| **Explore** | Re-scores lanes under operator-selected what-if scenarios. | Present hypothetical shocks as observed real-world events. |
| **Recommend** | Generates read-only enrichment and, when thresholds are met, disruptive mitigation proposals. | Automatically issue RFQs or reroute active purchase orders. |
| **Authorize** | Requires an explicit approval input for a disruptive action. | Treat a risk score as authorization. |
| **Simulate** | Returns an auditable, simulated result. | Change production bookings, contracts, suppliers, or logistics systems. |

The **Deny** control in the demo returns an operator-denial message and makes no booking change. The policy gate also rejects an unapproved disruptive execution attempt; that path is written to the local audit log.

## See the two scenarios

The screenshots below are captured from the repository's demo, not a live supply-chain feed.

| Energy: Gulf route | Energy: denied reroute |
| --- | --- |
| ![Energy scenario with simulated mitigation and operations confirmation boundary](docs/screenshots/01-energy-active-ops-confirms.png) | ![Hormuz scenario showing a denied unapproved reroute](docs/screenshots/02-energy-hormuz-reroute-denied.png) |
| Inspect the energy lane and its simulated operations workflow. | Attempt the disruptive action without approval; the gate denies it. |

| Semiconductors: denied dual-source action | Semiconductors: simulated reroute |
| --- | --- |
| ![Taiwan semiconductor scenario with an unapproved dual-source action denied](docs/screenshots/03-semi-conductor-taiwan-denied.png) | ![Taiwan semiconductor scenario showing the simulated approved reroute workflow](docs/screenshots/04-semi-conductors-taiwan-ops-confirm.png) |
| Explore concentration and single-source exposure without authorizing procurement changes. | Approve a proposed mitigation and inspect its simulated result. |

### Two operating views, one risk engine

| View | Audience | Workflow |
| --- | --- | --- |
| **Control tower** | COO, operations, risk, consulting | Select a tenant, filter lanes with a natural-language-style query, review the risk display, adjust scenario inputs, and compare results. |
| **Action desk** | Support and operations | Prioritize synthetic tickets alongside the scored lanes and see suggested next actions. |

The demo includes **Northwind Semiconductors**, **Gulf Harvest Imports**, and **Cinder Point Trading**, with separate seeded lanes, signals, and tickets.

## How BALLAST works

### 1. Explainable lane scoring

The risk engine starts with a baseline and combines lane delay, concentration, single-source exposure, relevant synthetic signals, and scenario adjustments. Scores are bounded to **0–99** and classified by deterministic severity thresholds.

```text
Risk score
  = baseline
  + delay contribution
  + concentration contribution
  + single-source contribution
  + matched-signal contribution
  + what-if scenario adjustment
  → clamp to [0, 99]
```

Every scored row includes risk drivers so reviewers can understand *why* a lane was ranked. The engine also provides an illustrative dollar-at-risk figure derived from the lane's annual value and score. **It is a modeling heuristic, not a validated financial-loss forecast or realized saving.**

The scoring rules and thresholds are inspectable in [`ballast/engine/risk.py`](ballast/engine/risk.py).

### 2. Scenario planning before action

The UI exposes four what-if inputs:

- Additional delay, in days.
- Tariff shock, as a percentage.
- A named port closure.
- A Taiwan typhoon overlay.

Re-running **Score lanes** applies the selected scenario to the seeded lane data. The control tower also uses the **same existing risk engine** to score those displayed lanes under an empty baseline scenario. It shows the baseline score, scenario score, actual score change, and newly displayed risk drivers side by side. Scores are capped at 99, so a lane already at the cap can show a zero increase despite additional shocks. This is a deterministic what-if comparison—not a forecast or an operational change.

### 3. Focused query parsing and tenant scoping

Operators can start with:

```text
Show me the top 5 risks to semiconductors from Taiwan in the next 30 days
```

or:

```text
Show me the top 5 risks to crude from the Gulf in the next 30 days
```

The current query parser extracts supported commodities, regions, top-N limits, and a requested day horizon. It is **rule-based parsing, not an LLM or unrestricted natural-language interface**. The parsed horizon appears in the brief but does not independently time-filter the underlying signals or produce a horizon-specific forecast.

The runtime loads lanes, signals, and tickets for the selected synthetic tenant before scoring. This demonstrates tenant-scoped retrieval, **not** production authentication or tenant-security isolation.

### 4. Link the control tower to the action desk

The ticket engine combines ticket age and the corresponding scored lane, where available, to prioritize the operations queue. Suggested responses include escalation, a draft dual-source note, or a customer update.

The result connects an executive risk view to an operational next step without claiming the ticket suggestion has already been sent or executed.

## Architecture

```text
Selected demo tenant + query + scenario
                 |
                 v
       Rule-based query parser
                 |
                 v
   Tenant-scoped SQLite data store
      lanes + signals + tickets
                 |
                 v
      Deterministic risk engine <--- what-if shocks
                 |
                 +--> ranked lanes, drivers, severity
                 +--> illustrative USD at risk
                 +--> mitigation proposals
                 |
                 v
         Ticket prioritization
                 |
                 v
   Control tower + action desk UI
                 |
          Operator selects action
                 |
                 v
          Python policy gate
          /              \
  no approval           approved
       |                   |
       v                   v
    DENIED          simulated result
       |                   |
       +--------+----------+
                |
                v
          Local audit events
```

| Component | Responsibility |
| --- | --- |
| [`ballast/engine/risk.py`](ballast/engine/risk.py) | Weighted lane scoring, scenario shocks, severity, risk drivers, and mitigation generation. |
| [`ballast/engine/nl.py`](ballast/engine/nl.py) | Deterministic parsing of supported query terms. |
| [`ballast/engine/tickets.py`](ballast/engine/tickets.py) | Prioritization of synthetic operations tickets. |
| [`ballast/governance/policy.py`](ballast/governance/policy.py) | Approval gate for disruptive actions. |
| [`ballast/runtime.py`](ballast/runtime.py) | Tenant-scoped analysis, action selection, simulated execution, and audit events. |
| [`ballast/memory/store.py`](ballast/memory/store.py) | SQLite-backed demo data and local JSONL audit logging. |
| [`ballast/ui/console.py`](ballast/ui/console.py) | Gradio control tower, action desk, what-if inputs, and operator controls. |

**Persistence:** the default SQLite database is `/tmp/ballast.db`; the local audit log is `data/audit/events.jsonl`, with a `/tmp` fallback if its normal directory cannot be created. The audit is useful for the demo, but it is not tamper-evident enterprise logging.

## Engineering decisions and trade-offs

### Deterministic scoring instead of a black-box prediction

The purpose of this prototype is to expose decisions, drivers, and control boundaries. A transparent weighted model makes it possible to inspect why a lane moved in the ranking and reproduce a scenario.

**Trade-off:** the weights, thresholds, and dollar-at-risk formula are illustrative. No trained time-series forecast, calibration study, or historical predictive-accuracy claim is provided.

### Synthetic signals instead of live AIS or news feeds

Seeded semiconductor, food, and energy scenarios make the demonstration repeatable and avoid presenting unverified external data as current logistics intelligence.

**Trade-off:** BALLAST does not ingest live AIS, weather, port, or news APIs; it should not be used to make real shipping decisions.

### Explicit authorization instead of silent automation

Proposing a reroute and executing one are different responsibilities. The runtime calls a separate policy gate before returning a simulated result for a disruptive action.

**Trade-off:** approval is a demo Boolean supplied through the UI/runtime, not identity-verified, role-based authorization. A production implementation would need authenticated operators, scoped permissions, workflow state, and downstream confirmation.

### A narrow orchestration layer instead of extra framework complexity

The pipeline is implemented as explicit Python components. There is no LangGraph dependency merely to label a deterministic workflow as multi-agent.

**Trade-off:** BALLAST does not demonstrate durable workflow orchestration, distributed jobs, live system integrations, or production retry semantics.

## Validation and limitations

The tests in [`tests/test_risk_and_gate.py`](tests/test_risk_and_gate.py) exercise the key demo behaviors:

| Test | Verified expectation |
| --- | --- |
| Taiwan semiconductor query | The parser extracts commodity, region, top-N, and the requested 30-day horizon. |
| Unapproved disruptive action | The policy gate raises a denial. |
| Scored semiconductor scenario | The selected tenant produces risk rows and an approval-required mitigation. |
| Runtime execution boundary | Unapproved execution returns `DENIED`; approval returns a `[SIMULATED]` result. |

These are focused regression tests, **not** comprehensive production validation. In particular, they do not establish statistical scoring accuracy, access-control isolation, end-to-end third-party integration, or correct execution in a real logistics network.

The control tower intentionally focuses on operational decisions rather than pricing. Its scenario comparison uses synthetic data and illustrative scoring; it does not establish financial-loss prediction, realized savings, or market validation.

## Run it locally

From a terminal with Python 3 available:

```bash
git clone https://github.com/TAM-DS/ballast.git
cd ballast
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open the local URL printed by Gradio (typically **http://127.0.0.1:7860**).

**Suggested five-minute walkthrough**

1. Select **Northwind Semiconductors**, keep the default Taiwan semiconductor query, and click **Score lanes**.
2. Inspect the baseline-versus-scenario comparison, ranked lanes, drivers, dollar-at-risk heuristic, recommended mitigations, and ticket actions.
3. Select **Open dual-source RFQ** or **Reroute active POs**. Click **Run** to see the unapproved action denied.
4. Select **Approve + execute** to see the simulated result. Alternatively, select **Deny** to take no action.
5. Apply the typhoon overlay or additional delay and **Score lanes** again. Compare each displayed lane's baseline and scenario scores and note any score cap before switching to **Cinder Point Trading** for the Gulf crude case.

Run the included tests:

```bash
python -m pytest tests/ -q
```

## Where BALLAST fits

[AEGIS Analyst](https://github.com/TAM-DS/aegis-analyst) applies a governed-action boundary to security operations. BALLAST applies the same architectural principle to supply-chain and procurement decisions.

In each domain, analysis can move quickly while disruptive authority remains explicit and constrained. The reusable idea is not a shared dashboard or an agent framework—it is the boundary between **what the system recommends, what a human authorizes, and what the execution layer can truthfully confirm**.

**A higher risk score may justify attention. It does not authorize a booking change.**
