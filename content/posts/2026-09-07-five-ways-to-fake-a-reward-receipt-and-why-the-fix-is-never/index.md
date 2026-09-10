---
title: "Five Ways a Reward Receipt Overstated Its Evidence"
date: 2026-09-07
lastmod: 2026-09-10
draft: true
author: "OpenAdapt Team"
tags: ["reinforcement-learning", "reward-modeling", "verification", "openadapt-flow"]
description: "Five reproduced defects in OpenAdapt's reward worker show how a grader can sign a result its evidence doesn't support, from a caller-chosen oracle tier to a calibration that rejects everything."
---

Point two oracle recipes at the same JSON file and ask OpenAdapt's reward worker to judge it. Name one `screen_dump`. Name the other `json_file`. Both route to the same `JsonDocumentOracle`, reading the same bytes. Here is what came back before the fix in [PR #463](https://github.com/OpenAdaptAI/openadapt-flow/pull/463):

```text
kind=screen_dump  sha256(file)=same  tier=0  certified=False  development_only=True   scalar=1.0
kind=json_file    sha256(file)=same  tier=2  certified=True   development_only=False  scalar=1.0
```

The bundle author changed one string. The worker gave the second receipt a higher evidence tier and marked it certified. The underlying read hadn't changed at all.

OpenAdapt's reward worker reads the system of record after a training episode and signs a `RewardEvidenceReceiptV1`. The receipt contains an outcome and a scalar reward. Its evidence tier and certificate state qualify that result. In this synthetic fixture, `certified=True` refers to a self-signed certificate with synthetic scope. It doesn't authorize production training or prove that OpenAdapt governed the policy's actions.

Our review found five ways the worker could sign a claim its read didn't support. Each had a concrete reproduction, retained in #463. The failures give anyone building an automated grader a useful test: trace each field in the result back to the mechanism that establishes it. A signature can't fix a result whose subject or evidence tier came from an unchecked caller choice.

## One JSON reader claimed two evidence tiers

`build_oracle` used the recipe kind to assign `json_file` to the `file` channel at tier 2 and `screen_dump` to `ocr` at tier 0. Both used the same reader. A local JSON document carried no evidence that it came from a system of record rather than a screen scrape.

The [adapter implementation](https://github.com/OpenAdaptAI/openadapt-flow/blob/44e99a48ebf048c18892aa17cef6ae594db0d0c2/openadapt_flow/reward/oracles.py) now owns its channel as a class attribute. Both JSON recipe kinds use `ocr` at tier 0. The builder checks that the adapter and recipe table agree, and bundle loading refuses a contract that declares a different channel. A `json_file` contract declaring `file` now fails to load.

SQLite still reaches tier 2 through a read-only database query, with a header check that rejects a JSON file renamed to look like a database. That check establishes the read mechanism. Establishing who controls the database remains a separate trust decision.

The same limit applies to the REST and FHIR adapters. They can verify that they made a network call; they can't establish that an arbitrary endpoint is the customer's system of record. The person or service that admits the bundle owns that check. Calling a trainer-controlled server over HTTPS wouldn't make its answer independent.

## The trainer could replace the registered subject

The old worker chose `declared_identity or registered_identity`. The descriptor arrived after the rollout and took precedence over the subject that the environment registered before it ran.

The reproduction registered `patient-lie-0002`, then submitted a descriptor naming `patient-honest-0001`. The worker returned `verified`, scalar `1.0`, and a receipt naming the second identity. These are synthetic MockMed identifiers. The worker had signed a result for a different subject from the one assigned to the episode.

The [worker](https://github.com/OpenAdaptAI/openadapt-flow/blob/44e99a48ebf048c18892aa17cef6ae594db0d0c2/openadapt_flow/reward/worker.py) now uses the registration to select the subject. A conflicting descriptor gets HTTP 422 with `identity_conflict`; re-registering the episode under another subject gets HTTP 409. Repeating the same registration before scoring remains allowed and refreshes the baseline.

This protects the subject recorded at registration. The environment must still register before actuation, and whoever controls registration remains part of the trust boundary. The worker can't reconstruct the true order of an external rollout from a descriptor alone.

## An episode could earn reward without changing the store

The seeded contract originally required `record_written` without `count_new_only`. That assertion inspected what the store held when the worker read it. A row left by an earlier episode could satisfy it. The retained reproduction ran no episode and still got `verified` with scalar `1.0`.

The fix requires at least one required effect that asserts change: `count_new_only` or `exact_new_set`. The judge compares that effect with the pre-episode baseline. Other required effects, such as a field read-back, can accompany it because the worker requires all of them to pass. [Bundle validation](https://github.com/OpenAdaptAI/openadapt-flow/blob/44e99a48ebf048c18892aa17cef6ae594db0d0c2/openadapt_flow/reward/models.py) refuses a contract whose required effects only describe the current state.

In the corrected fixture, doing nothing earns `wrong_effect` with scalar `0.0`. So does relying on a row that was already there. A missing baseline instead makes the read indeterminate and the episode unscored.

That changes which contracts the worker accepts. A task that intentionally checks existing state needs a different contract design; it can't use this worker's change requirement as evidence that an episode did useful work.

## Counting backward made an expired certificate current

The trainer supplied `policy_update`, and the worker used it to decide whether the certificate had expired. In the reproduction, updates `0` and `999` were current, `1000000000` was expired, and a later `0` made the same certificate current again.

The worker now persists the highest update it has scored for the contract. A later descriptor below that value gets HTTP 422 with `policy_update_regressed`. The counter belongs to the contract, so renaming a policy checkpoint doesn't reset it. The [regression tests](https://github.com/OpenAdaptAI/openadapt-flow/blob/44e99a48ebf048c18892aa17cef6ae594db0d0c2/tests/test_reward_trust_boundary.py) exercise both a decreasing counter and a renamed checkpoint.

This enforces monotonicity over reported updates. It doesn't measure optimizer steps independently. The trainer still supplies the number, so holding it constant is outside what this check detects. An expired certificate also doesn't erase the effect verdict: a receipt can remain `verified` and scored while `certified` is false.

## Rejecting everything produced the best calibration bound

The old calibration generator always planted `Triage` records. A contract asking for `Radiology` rejected every generated store, even when the planted fault had nothing to do with the rejection. The retained run reported 300 trials, zero false accepts, and `epsilon=0.009936`.

That number bounds false accepts under the sampled synthetic fault distribution. It isn't an error bar around the scalar reward. Here the test couldn't tell a grader that caught the planted faults from a grader that rejected everything.

The [calibration code](https://github.com/OpenAdaptAI/openadapt-flow/blob/44e99a48ebf048c18892aa17cef6ae594db0d0c2/openadapt_flow/reward/calibration.py) now derives its synthetic records from the contract's required and forbidden effects. Before it counts faults, it runs a clean control built from those effects. The control must earn `VERIFIED`, or calibration stops. A contract with no applicable fault class also fails calibration.

The generator covers six fault classes: a wrong subject, a wrong field value, an extra record, a duplicate record, a missing record, or a forbidden record. Each trial has a pre-state. The certificate and its policy must name the derived corpus digest, and the calibration metadata records which fault classes applied.

With zero false accepts in 300 trials, the one-sided Clopper-Pearson upper bound at 95% confidence still rounds to `0.009936`. The count determines the number. The control and the contract-derived cases determine whether that count answers the intended question. These synthetic trials don't establish a production error rate, and a clean control alone doesn't measure how often valid real episodes would be refused.

## Inspect the released worker

[Flow 1.35.1](https://pypi.org/project/openadapt-flow/1.35.1/) was published on September 9, 2026. Its wheel declares the `reward` extra and contains the reward modules and `serve-reward` command. The release includes the fixes above. The earlier installation warning referred to 1.34.0; the tagged reward guide still carries that stale warning.

To install the version discussed here:

```bash
pip install 'openadapt-flow[reward]==1.35.1'
```

The [reward guide at that release](https://github.com/OpenAdaptAI/openadapt-flow/blob/44e99a48ebf048c18892aa17cef6ae594db0d0c2/docs/REWARD_WORKER.md) describes the local MockMed setup and its self-signed synthetic certificate. It also distinguishes an unscored receipt (`scalar_reward: null`) from a wrong effect scored at zero. An unavailable store must preserve that distinction all the way into the trainer.

For your own grader, start with its registration and result interfaces. Try changing the subject between them. Keep the evidence bytes fixed while changing the declared channel. Run a valid control before trusting a zero false-accept count. Preserve the rejected requests beside the accepted ones so a reviewer can check exactly which claim each refusal protects.
