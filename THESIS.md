# Handoff: "Open Loops That Nobody Owns" — Agent Idea

This document is a complete handoff of a single agent product idea, developed through discussion. It contains the full concept, target track decision, reasoning, mechanics, and open questions. No part of this should be considered final copy for public use — it's the working idea in full detail, for another agent/collaborator to pick up and build on.

---

## 1. The Core Problem

Human systems constantly create "open loops": a commitment is made with an implied or explicit deadline for resolution, but no single system or person owns watching it through to completion.

Examples of loop-opening events:
- A referral is made (e.g., doctor refers patient to a specialist)
- A test is ordered
- A warranty claim is filed
- A permit application is submitted
- A supplier promises a delivery date
- A doctor says "come back if it doesn't improve"
- A form is submitted to an office that never confirms receipt

Each of these has:
- A **start event** (something was promised or initiated)
- An **expected resolution window** (explicit or implied)
- A **termination event** that should occur (confirmation, outcome, delivery, follow-up)

The termination event frequently never happens — not because anyone failed at their job, but because **no one owns the space between start and finish**. The loop closes only if a human happens to remember to check. There is no error message for something that simply didn't happen. Silence is indistinguishable from "handled" until it isn't.

## 2. Why This Is Hard / Why Humans Struggle With It

- **Loops span organizations.** The person who opens the loop (a specialist, a clerk, a vendor, an office) has no visibility into whether it closed on the other end, and no incentive structure that reaches across that organizational boundary.
- **The person who bears the consequence often doesn't know a loop exists.** The patient doesn't know the referral was never scheduled. The applicant doesn't know the permit stalled.
- **Existing software tracks tasks inside one system.** Loops live *between* systems, in the gaps — created implicitly in prose (an email, a phone call, a fax, a verbal promise), not as structured tickets.
- **Ticketing/CRM systems only solve this where one company owns both ends of the loop.** They require a human to explicitly create the tracked item. They have no mechanism for inferring a commitment from an unstructured sentence.
- **The "checking back" work itself becomes a full-time burden.** For professionals whose job involves managing many parallel commitments, the manual re-checking of dozens/hundreds of open threads consumes time that should go toward actual judgment calls.

## 3. Why Existing Tools Don't Solve It

- CRMs, project management tools, and ticketing systems require **explicit, structured creation** of a tracked item by a human.
- The entire difficulty is that open loops are created **implicitly, in prose**, across parties who use different (or no) shared software.
- Detecting a loop from an unstructured sentence, and then pursuing it across an organizational boundary until it closes, is specifically the kind of task that requires an agent (versus a static tracking tool).

## 4. The Agent's Role / Mechanics

The agent would:

1. **Maintain a registry of every open loop**, inferred from the user's (or professional's) communications, documents, portals, and records. For each loop it would capture:
   - What was promised
   - Who is responsible (the counterparty)
   - The expected resolution window
   - What evidence would count as closure (e.g., a confirmation email, a status change in a portal, a delivered item, a scheduled appointment)

2. **Poll for closure evidence** across relevant channels/systems as the resolution window approaches and passes.

3. **Escalate in stages when a loop passes its window without resolution:**
   - Stage 1: Re-query the system of record (check the portal, check for an update, check email threads again)
   - Stage 2: Contact the responsible party directly (a drafted follow-up email/call script to the specialist's office, the supplier, the agency)
   - Stage 3: Surface to the human with a **drafted intervention** — i.e., don't just alert, hand them something ready to send/act on

## 5. Before vs. After

- **Before:** You find out six months later that the referral was never scheduled, the tax amendment was never processed, the supplier never confirmed. The failure surfaces only when the consequence has already landed.
- **After:** Unresolved things become visible **while they are still cheap to resolve** — days or weeks after the window lapses, not months.

## 6. The 10x Effect — Why This Matters at Scale

- The gain is not time saved. **The gain is failures prevented.**
- In medicine: studies of abnormal test-result follow-up consistently find meaningful fractions go unacknowledged. Exact numbers vary by setting, but the phenomenon is well documented and occasionally fatal. (Note: this is a directional claim from the original brainstorming — would need to be sourced/cited properly before use in any real pitch.)
- In business: the same failure mode shows up as slipped deliveries, expired options, lapsed renewals, unconfirmed compliance filings.
- **A large share of what project managers, case managers, medical assistants, and expediters do all day is manual loop-chasing** — i.e., this isn't a niche inefficiency, it's a substantial fraction of certain job categories' actual daily labor.

## 7. Unexpected / Second-Order Consequence

Once loop closure is reliably tracked and audited over time, **the reliability of every counterparty becomes measurable.** You'd get an empirical map of which institutions, vendors, or offices actually finish what they start.

- This is a form of **accountability infrastructure that has never existed** in most of these domains.
- Practical byproduct: a professional (e.g., a case coordinator) could develop something like a **vendor/counterparty reliability scorecard** — which labs confirm results promptly, which suppliers actually hold their dates — as a natural, sellable side effect of the core tracking function.

## 8. Strongest Self-Objection (and how it was resolved)

**Objection:** Most open loops are low-stakes noise. An agent that surfaces *all* open loops just recreates the original attention problem — now the human has a long list of alerts instead of a long list of loose ends. **Triage — deciding which loops actually matter — is the real hard part, not detection.**

**Resolution reached in discussion:**
- This objection is much harder to solve for an **individual/consumer user**, who has no domain expertise to lean on for triage and would likely just get an undifferentiated pile of notifications.
- It's **much more tractable for a professional user** (case manager, coordinator, expediter), because:
  - They already possess the professional judgment needed to rank loops by stakes (e.g., a missed biopsy follow-up vs. a routine reorder).
  - The agent's job is not to invent a priority model from scratch — it's to surface the registry with enough signal (age past window, stated stakes in the original text, prior escalation history, counterparty reliability history) that the professional's **existing judgment** can triage quickly.
  - This reframes the product from "an agent that decides what's important" to "an agent that removes the manual-checking labor so the professional can spend all their time on the triage/judgment they're already good at."

## 9. Track Decision: Professional Agents (not Everyday, not Good Neighbor)

Three possible tracks were considered:
1. **Everyday Agents** — busywork out of daily personal life (home, money, health, errands, family), running quietly and pinging only for real decisions.
2. **Professional Agents** — making someone dramatically better at work they already do; repetitive, judgment-heavy tasks that eat their day.
3. **Good Neighbor Agents** — helping groups (neighborhoods, nonprofits, food banks, schools, libraries).

**Decision: This idea is explicitly targeted at Professional Agents**, per the user's direction — even though the original brainstorming examples (doctor referrals, warranty claims, permits) read more naturally as personal-life examples. The task was to reframe the *same core mechanic* around a professional protagonist rather than an individual consumer, without changing the underlying idea.

**Why Professional Agents fits, once reframed:**
- Target user is not "a person with a life" but **a person managing many other people's/entities' loops as their actual job**: case managers, medical referral/care coordinators, permit expediters, insurance claims handlers, project/account managers.
- The problem statement, why-humans-struggle section, and agent mechanics all translate directly — just scaled from "one life's worth of loops" to "an entire caseload's worth of loops."
- The triage objection (Section 8) resolves *better* under this framing, because the professional already has domain judgment to apply to a well-organized worklist, whereas an individual consumer does not.
- The 10x-effect stats (test-result follow-up failures, project slippage) stop being illustrative background and become **the direct value proposition** for this exact job category.
- The unexpected consequence (counterparty reliability scoring) becomes a concrete, sellable feature for a professional/business context, rather than a vague societal-infrastructure claim.

**Recommended anchor persona (not yet finalized, just a working recommendation):** Medical referral / care coordinator — chosen because it's the highest-stakes example already present in the original material, and "abnormal test result follow-up" is a well-documented, citable failure mode that would strengthen any pitch or demo.

## 10. Open Questions / Not Yet Decided

- Final target persona: medical referral coordinator vs. permit expediter vs. insurance claims handler vs. generalized "case manager" — one should likely be chosen and built around specifically, per earlier guidance that a judge/evaluator wants to see the mechanic proven for one concrete person before generalizing.
- How the agent actually gets visibility into the professional's communications/documents/portals in practice (data access, integrations, permissions) — not yet specified.
- How "expected resolution window" is inferred when not explicitly stated (e.g., a promise with no stated deadline) — not yet specified.
- What the actual UI/workflow looks like for the professional reviewing the registry and drafted interventions — not yet specified.
- Sourcing/citation needed for the medical follow-up statistics before using them in any real pitch — currently a directional, unsourced claim from brainstorming.
- Naming for the product/concept has not been decided (working descriptions only: "open loops," "loop registry," "accountability infrastructure").

## 11. Explicit Non-Direction (per user instruction)

- Do **not** frame this as an Everyday Agent (personal-life) product, even though several of the original illustrative examples read that way. The professional framing is the committed direction.
- Do **not** frame this as a Good Neighbor Agent (community/nonprofit-facing) product — this was considered and explicitly deprioritized as the weakest fit, since it drifts toward a surveillance/accountability angle that isn't the core value proposition.
- Public-facing posts about this idea (see companion teaser post) are intentionally written to **not reveal** the loop-registry/detection/escalation mechanism — only the problem framing. This handoff document, by contrast, is meant to contain full detail for internal/collaborator use.
