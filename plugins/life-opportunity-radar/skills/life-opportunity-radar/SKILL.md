---
name: life-opportunity-radar
description: Search current primary-source signals for long-term opportunities with accessible entry, compounding ownership, explicit downside, and falsifiers. Use for unfamiliar paths, strategic opportunity scans, direction changes, or evidence that may reorder existing bets; do not use for ordinary news summaries or unrelated factual questions.
---

# Life Opportunity Radar

Treat the user's input as a signal seed, not necessarily a fully formed question. If it is vague but plausibly strategic, start a bounded current scan and state the inferred connection.

Read [references/search-and-scoring.md](references/search-and-scoring.md) for source hierarchy, scan coverage, scoring, and output states. Read [references/strategy-profile.example.md](references/strategy-profile.example.md) only when personal-fit scoring matters. The example is a schema, not user data.

## Outcome

Find changes that create a realistically accessible path to substantial long-term upside. Prefer overlooked enabling layers, falling entry gates, under-supplied infrastructure, new distribution routes, and disconfirming evidence over generic trend news.

The goal is not to maximize ideas. It is to make the user's direction set more accurate by adding, upgrading, downgrading, or rejecting paths.

## Invocation behavior

- A named company, tool, paper, job, protocol, claim, or industry becomes the seed for a focused scan.
- A broad strategic question triggers a cross-domain scan.
- Continue from known paths stated in the current conversation or a user-provided local profile. Do not present a renamed known trend as a discovery.
- If the user asks an unrelated direct question, answer it normally.

## Required current research

Use current web research for every radar scan. Search in the user's language and English when useful. Prefer primary sources and distinguish the publication date from the date of the underlying event.

Look beyond front-end products. Check the surrounding stack when relevant:

- capability packaging and workflow systems;
- evaluation, benchmarks, observability and replay;
- security, permissions, provenance and compliance;
- data, synthetic scenarios and human feedback;
- routing and unit economics;
- protocols, interoperability and distribution;
- buyer demand, open-source adoption and lowered permission gates.

Use media, social posts, newsletters and aggregators to discover leads, not as sufficient proof. For consequential claims, seek an official document, repository, paper, standard, pricing page, procurement record, job specification, customer artifact, or other first-party evidence.

## Fit without hidden profiling

- Use only constraints the user provided in the current conversation or deliberately placed in a local strategy profile.
- If a decisive fit variable is missing, mark it `UNKNOWN`; do not infer education, wealth, health, family situation, location, personality, or risk tolerance from weak cues.
- Separate industry attractiveness from the individual's actual permission to enter.
- Prefer a three-year capability and ownership trajectory over market-size slogans.
- Identify what compounds: skill, code, data, audience, IP, distribution, reputation, certification, or nothing.
- Do not promise a probability of life change when no defensible base rate exists.

## Analysis discipline

For every serious candidate, separate:

- **CONFIRMED:** directly supported current facts or user-reported evidence;
- **INFERENCE:** fit, timing, or business-model judgment;
- **UNKNOWN:** missing evidence that could reverse the conclusion.

Answer:

1. What changed, and why does it matter now?
2. What exact value position could an individual own?
3. Who controls entry, and can public proof-of-work bypass the gate?
4. What compounds after three years?
5. What are the technical, social, capital, legal, geographic, language and health gates?
6. What is the worst realistic loss?
7. What observable evidence would falsify the path?
8. Does the signal add, upgrade, downgrade, reject, or leave unchanged an existing direction?

Do not confuse industry growth, investment, job existence, GitHub stars, or a viral demo with accessible personal opportunity.

## Default response

Reply in the user's language and lead with the strategic consequence. For a pulse scan, return only the strongest three to five signals. For each signal include:

- signal and primary source;
- what is genuinely new;
- possible individual position;
- entry gate and main trap;
- state: `WATCH`, `PROBE`, `BET CANDIDATE`, or `REJECT`;
- effect on the existing direction ranking.

End with one high-information question only when its answer would materially change the next scan.

## Persistence and privacy boundary

Do not silently create or rewrite a personal profile. Ask before saving strategic context. Keep any real profile outside this public skill repository, never echo sensitive details unnecessarily, and never treat the example profile as facts about the user.
