---
title: "We already run UiPath. Where does OpenAdapt fit?"
date: 2026-08-26
lastmod: 2026-10-09
author: "Richard Abrich"
# Rewritten 2026-10-09 for business readers. See .overhaul/REWRITE_PLAN.json.
# UiPath prices were read by hand from https://www.uipath.com/pricing on
# 2026-10-09. Re-read the page on the day this post is promoted and update the
# date in the text. The pricing page's Healing Agent tier mapping wasn't clear
# on that check, so the post doesn't repeat it.
tags: ["comparison", "uipath", "rpa", "gui-automation"]
description: "Keep UiPath for the program it runs. OpenAdapt takes the last step of one task: it enters approved data, checks that it saved, and stops on a mismatch."
thesis: "Keep UiPath for the program it runs and let OpenAdapt take one task's last step: enter approved information, check that it saved, and stop for a person on a mismatch."
audience: "business"
post_type: "comparison"
---

If your team already runs UiPath, keep it. OpenAdapt doesn't replace an automation program. It takes the last step of one task off your team: entering approved information into a system such as an EMR or a payer portal, and checking that it saved. When something doesn't match, it stops and asks a person instead of guessing.

## What UiPath already does for you

According to UiPath's [Orchestrator page](https://www.uipath.com/product/orchestrator), you use Orchestrator to deploy and start attended and unattended robots and to monitor their work. It logs what each robot does and can run in UiPath's cloud or on your own servers.

A program with hundreds of automations also needs someone to own each one and to control how changes roll out. UiPath has spent years on that work.

As of 2026-10-09, UiPath's [pricing page](https://www.uipath.com/pricing) lists Basic as starting at $25 per month and asks you to contact sales for Standard and Enterprise. The page also says an updated plan offering is coming soon.

## Where OpenAdapt fits

Here's how OpenAdapt handles that step:

1. A person shows the task once while OpenAdapt records it.
2. OpenAdapt builds an automation from the recording. A normal run follows it without calling an AI model.
3. Before it types, it checks that it's in the right patient's record.
4. After it saves, it reads the record back from the system to confirm the change.
5. When something doesn't match, it stops and asks a person. If a save may have gone through, a person checks the record before anything is retried.

Before go-live, a readiness test runs the automation on your system with your own cases and shows which steps carry each check. If a screen changes later, OpenAdapt finds the same field again or stops. A person approves any fix it proposes.

The record check needs its own way to read the record, such as an API or a separate login. Without one, OpenAdapt can still stop when the screen looks wrong, but it won't report a run as done and checked.

UiPath can run similar checks when your developers build them in. In OpenAdapt, the checks are part of the automation you test.

## What changes in your team's day

This is an illustration, not a customer result. Say your UiPath process already reads faxed referrals and extracts the details, and a staff member keys each approved referral into the EMR. Two hospital studies put that manual work at 10 to 12 minutes per referral ([UCSF, JAMIA Open 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7660949/); [an NHS trust, HFMA case study 2024](https://www.hfma.org.uk/system/files/2024-04/Using%20digital%20technologies%20to%20process%20admin%20tasks%20Case%20Study%20v7.pdf)).

| Step | Today | With OpenAdapt on the last step |
|---|---|---|
| Read the referral and extract the details | Your UiPath process | Unchanged |
| Type the referral into the EMR | A staff member | OpenAdapt, on a computer you control |
| Confirm it's the right patient | A staff member, by eye | OpenAdapt, before it types |
| Confirm it saved | A staff member, by reopening the chart | OpenAdapt reads the saved record back |
| What comes back to staff | Every referral | The referrals it stopped on, with the reason, plus a receipt for each finished entry |

A receipt records what OpenAdapt entered and how it checked it.

We haven't measured time saved in a deployment like this, so there's no number here. The NHS trust's robots still left about 1 in 20 referrals to staff, such as complex cases and data quality problems. Expect OpenAdapt to stop on some referrals too, such as a patient it can't match, and count that review work on the "after" side.

## How the two would connect

There's no published OpenAdapt connector for UiPath today. You could connect them across a normal process boundary: your UiPath process would hand one case to OpenAdapt and act on the result it returns. Before that design handles real cases, it needs identity, authorization, and audit design in your environment, plus a way to keep the same case from being entered twice.

| Result OpenAdapt returns | What it means | What your process does next |
|---|---|---|
| Done and checked | It saved the entry and read the record back to confirm it. | Continue the case. |
| Stopped before saving | Something didn't match, so it stopped before changing anything. Nothing was written. | Send it to a person. After they fix the cause, it can run again. |
| Check the record | A save may have gone through. | Send it to a person to check the record. Don't retry until they have. |
| Didn't finish | It couldn't complete the task. | Send it to a person, with what's known about whether anything was written. |

If your process retries failed jobs on its own, leave the last two results out of that retry. Retrying after a save that may have gone through can enter the same referral twice.

## When UiPath alone is enough

If a UiPath robot already makes the entry and your team trusts the result, you don't need OpenAdapt for that task. If the system has an API that can make the change, use the API. OpenAdapt is for the step that only happens on screen, where you want each entry checked against the record. For a feature-by-feature view, see the [OpenAdapt and UiPath comparison](https://openadapt.ai/compare/uipath).
