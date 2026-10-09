---
title: "An empty evidence list isn't proof of no effect"
date: 2026-07-28
lastmod: 2026-10-09
draft: true
slug: "empty-evidence-list"
author: "OpenAdapt Team"
# Rewritten 2026-10-09. See .overhaul/REWRITE_PLAN.json. The post was never
# published, so the old folder URL needs no alias. Whether to publish
# (draft: false) is the founder's call.
tags: ["safety", "verification", "engineering", "postmortem", "openadapt-flow"]
description: "A bug in OpenAdapt's run classifier read an empty evidence list as proof that nothing was saved. Here's the fix and how to find the pattern in your code."
thesis: "An outcome that claims nothing happened needs proof that something was checked, because a loop over an empty evidence list gives the same answer as a clean check."
audience: "developer"
post_type: "essay"
---

A loop that searches a list for problems reports "no problems" when the list is empty. In OpenAdapt Flow, that answer once decided whether a person was told a halted run had saved nothing. If a run stopped before its effect check started, the evidence list was empty, the check found nothing uncertain, and the run was labeled as stopped before saving, even when the save might have gone through. [PR #280](https://github.com/OpenAdaptAI/openadapt-flow/pull/280) fixed it on July 27, 2026, and its description calls it a P0 soundness defect. The same shape can turn up wherever a status enum has a fallthrough branch, so the fix applies outside Flow too. An outcome that claims something didn't happen should be reachable only through a path that shows a check ran.

## How an empty list became a clean result

[PR #259](https://github.com/OpenAdaptAI/openadapt-flow/pull/259) gave Flow explicit terminal outcomes a day earlier. Each one says what's known about a run's effect on the system of record, the application where the data lives. These are the outcomes this bug touches:

| Outcome | What it claims | What the person who reads it does |
|---|---|---|
| `VERIFIED` | The change was saved, and a read of the record confirmed it | Nothing |
| `HALTED_BEFORE_EFFECT` | The run stopped before saving anything | Nothing to check |
| `REJECTED_POLICY`, `CANCELED`, `FAILED_PLATFORM` | A policy refusal, a cancellation, or a platform fault stopped the run before any save | Nothing to check |
| `RECONCILIATION_REQUIRED` | A save may have gone through | Checks the record before anything is retried |

`classify_transaction_outcome()` picks the outcome. Before the fix, its path for a halted run looked like this, simplified from `openadapt_flow/transaction.py`:

```python
def _has_unresolved_uncertainty(report):
    for result in report.results:
        uncertainty = result.delivery_uncertainty
        if uncertainty is not None and not uncertainty.resolved_by_contract:
            return True
        for evidence in result.effect_evidence:  # empty if the check never ran
            if evidence.final_verdict == "indeterminate":
                return True
            if evidence.final_verdict == "refuted" and evidence.observed_effect != "absent":
                return True
    return False  # same answer for "checked, all clear" and "never checked"


def classify_transaction_outcome(report):
    ...
    if _has_unresolved_uncertainty(report):
        return TransactionOutcome.RECONCILIATION_REQUIRED
    ...
    if report.execution_outcome == "HALTED":
        # A governed halt with the verifier having established no effect.
        return TransactionOutcome.HALTED_BEFORE_EFFECT
```

Follow a run that aborts early through that code. The run halts before the effect check starts, so `effect_evidence` is empty for every step. The inner loop never runs, and the function returns `False`. The classifier reads that as "nothing uncertain," finds no policy refusal and no cancellation, and reaches the `HALTED` branch. The comment on that branch says the verifier established that no effect happened. On this path, the verifier never ran.

Each piece is correct on its own terms. The loop does what its name says, and the classifier trusts a helper that answers a question about uncertainty. The defect sits between them. `False` meant "I found no uncertain reading," and the caller took it to mean "the check found no effect." Those are two different facts, and an empty list makes them look identical.

## What a person would have seen

The reproduction in [openadapt-evals PR #272](https://github.com/OpenAdaptAI/openadapt-evals/pull/272) runs a fake clinic app's fault server and compares each reported outcome with the server's own store. In one case, the backend commits the row and then hangs past the client's timeout. The run halts because it never got an answer. Before the fix, it reported `HALTED_BEFORE_EFFECT` while the store held the new row.

Picture the person on the other end. They see that the run stopped before saving, so they have no reason to open the record. The row sits in the system of record with nothing pointing at it. That's the silent wrong save the record check was built to catch, and here the outcome table let it through.

The tests that shipped with the classifier passed with the bug in place. A test where verification runs fills the evidence list, so this bug needs an input that's easy to forget, a run where verification never started.

The PR found the same shape in two more places:

- `_attempt_state()` returned `not_actuated`, meaning the step never sent its action, whenever nothing had recorded a delivery. A step whose delivery wasn't recorded either way now gets `delivery_uncertain`.
- `build_effect_journal()` treated a failed lookup of a workflow step as proof that the step couldn't write, and dropped it from the journal. A step whose own fields say it could write now stays in.

## Make the code prove absence

The rule PR #280 put in place fits in one sentence. No outcome may claim that nothing happened while any step that could change data has an unknown effect. For each such step, one of these has to be true:

1. A verifier read the system of record and found none of the effects the step declared, with each effect checked exactly once.
2. The runtime recorded, at the time, that the step stopped before it tried to deliver its action.

If neither holds, the run reports `RECONCILIATION_REQUIRED`, and a person checks the record before anything is retried. The guard covers all 4 outcomes that claim nothing changed. Simplified again:

```python
def _effect_absence_proven(result):
    if result.effect_evidence:
        # Every declared effect read back exactly once, and each one absent.
        return _effect_evidence_has_exact_coverage(result) and all(
            e.final_verdict == "refuted" and e.observed_effect == "absent"
            for e in result.effect_evidence
        )
    # No readings at all: only a recorded stop before delivery counts.
    return _attempt_state(result) == "not_actuated"


# In classify_transaction_outcome(), before any outcome that claims no effect:
if _lacks_effect_absence_proof(report):  # a step that could write, unproven
    return TransactionOutcome.RECONCILIATION_REQUIRED
```

An empty list now takes the second branch, and that branch asks for a positive record. `_attempt_state()` got stricter in the same way. It returns `not_actuated` only for a skipped step, a gate that refused before acting, or a step the replayer marked as never attempted. A failed postcondition now counts as proof that the action went out, because postconditions are checked after the click.

[PR #264](https://github.com/OpenAdaptAI/openadapt-flow/pull/264), from the same day as #259, applies the idea to the verifiers. A verifier adapter returns one of 6 results: `CONFIRMED`, `REFUTED`, `UNAVAILABLE`, `STALE`, `CONFLICTING`, or `INDETERMINATE`. "I couldn't read the record" has its own names, `UNAVAILABLE` and `INDETERMINATE`, so it can't land where "I read the record and the change isn't there" lands. Only `CONFIRMED` lets a run continue.

The fix has a cost. In the `ap_invoice` and `o2c_recon` benchmark suites, some scenarios have an API gateway refuse the write, and a direct read of the state shows nothing changed. The runtime itself never read the system of record after it sent the request, so it can't prove that, and those runs now report `RECONCILIATION_REQUIRED`. Someone checks a record that turns out to be fine. We'd rather pay that than tell a person a write didn't happen when it might have.

At the merge, `tests/test_transaction_outcome.py` held 49 tests, up from 25. Two of the new tests are a matched pair that drive the real replayer. In the first, the click reaches the app, the "Saved" text never appears, and the run aborts with an empty evidence list, so it has to report `RECONCILIATION_REQUIRED`. The PR's description says this test reproduces the bug on the old code. In the second, the replayer never finds the button, nothing is clicked, and the run still reports `HALTED_BEFORE_EFFECT`. A run that can prove it stopped before saving keeps the clean outcome.

## Find the same branch in your code

You don't need Flow's types to use this. Look for any enum where a member claims that something was checked and came back clean, such as "no effect," "not found," "no match," or "safe to retry." Then:

1. List every member of that kind.
2. Find every code path that returns one, including `default` and `else` branches.
3. For each path, write down what it inspected. If the only answer is that nothing else matched first, the path is a fallthrough.
4. Send the fallthrough to an explicit unknown state, and make the clean state require a reading.
5. Add a test where the check never runs, such as an empty evidence list, a verifier that's never called, or a timeout before the read.

OpenAdapt applies the same rule to the messages people read. Only an outcome that proves the run stopped before any save may say "nothing was written" or "safe to try again." When the outcome can't prove that, the message tells a person to check the record before anything is retried.
