---
title: "We use Power Automate. Where does OpenAdapt fit?"
date: 2026-08-26
lastmod: 2026-10-09
draft: false
author: "Richard Abrich"
# Rewritten 2026-10-09 for operations leaders; see .overhaul/REWRITE_PLAN.json.
# Microsoft's prices were checked again on 2026-10-09. Check them on the day
# this post is promoted.
tags: ["comparison", "power-automate", "rpa", "gui-automation"]
description: "Keep Power Automate for the work its connectors reach. Add OpenAdapt for the last entry that only happens on screen and needs the saved record checked."
thesis: "Use Power Automate's connectors wherever they reach; use OpenAdapt for the last screen-only entry, where you need the saved record checked and a person asked when something doesn't match."
audience: "business"
post_type: "comparison"
---

If your team already runs Power Automate, keep using it for every step its connectors reach. OpenAdapt is for the step they can't reach. That's usually the last one, where someone types approved information into a screen such as an EMR form or a payer portal. OpenAdapt enters the information, confirms it in the saved record, and asks a person when something doesn't match.

## What Power Automate already does well

Work that moves between Outlook, Excel, Dataverse, Teams, and SharePoint already has connectors in Power Automate. A connector moves the data without opening a page or clicking a button, and your administrators already manage connectors. Use that path first, before any screen automation, ours included.

For Windows apps with no connector, Power Automate for desktop has a recorder that [tracks mouse and keyboard activity against the app's UI elements](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow) and turns it into desktop and browser actions. It can capture UI Automation selectors, which find fields in newer Windows apps, and MSAA selectors for older ones.

Microsoft's [pricing page](https://www.microsoft.com/en-us/power-platform/products/power-automate/pricing) listed these plans on 2026-10-09, all paid yearly:

| Plan | Price | Includes |
|---|---|---|
| Premium | $15 per user a month | Cloud flows; desktop flows while someone is signed in |
| Process | $150 per bot a month | Cloud flows; desktop flows that run on their own |
| Hosted Process | $215 per bot a month | Process, on a virtual machine Microsoft hosts |

Our [Power Automate comparison](https://openadapt.ai/compare/power-automate) sets these beside OpenAdapt's costs.

## Where a connector stops

Some changes exist only in a form on screen, because the connector can't write that record or there's no API for the change. A desktop flow can still fill in the form and click Save.

The flow's author can then add a step that confirms the save by reading the record through an API or a database query, if the system offers one. In [our fault test](/posts/silent-wrong-action/) on an app we built for testing, a check that trusted only the success message passed most of the saves that left the record wrong.

## What OpenAdapt adds at that step

You show OpenAdapt the task once, and it builds the automation from that recording. It works in web apps and Windows desktop apps, though our Windows testing covers only a few apps so far. Before any automation goes live, we test it on your system with your own cases. Each run has four steps:

1. Before it types, it checks that the screen shows the intended patient or account.
2. It enters the approved information and saves.
3. It reads the saved record back by a separate route, such as a read-only API, a database query, or a second session.
4. If anything doesn't match, it stops and asks a person.

If the screen changes, OpenAdapt finds the same field again or stops. Each run ends with one result:

| Result | What it means for your team |
|---|---|
| Done and checked | It saved the entry and confirmed it in the record. |
| Stopped before saving | Something didn't match, so it changed nothing. A person takes the case. |
| Check the record | The save may have gone through, for example if the app froze after Save. OpenAdapt won't send it again. A person checks the record before anyone retries. |
| Didn't finish | Its report says what's known about whether anything was written. |

## One referral, before and after

In this illustration, a clinic on Microsoft 365 gets referrals by fax, and its EMR has no connector for creating them.

| Step | Today | With OpenAdapt |
|---|---|---|
| Fax arrives and is approved | A cloud flow files it in SharePoint and asks for approval in Teams. | No change |
| Referral entered in the EMR | Staff type it in. | OpenAdapt enters it. |
| Save confirmed | Staff look at the screen. | OpenAdapt reads the referral back from the EMR. |
| Something doesn't match | Staff sort it out as they type. | The run stops, and staff get the referral and the mismatch. |

A [UCSF time study (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7660949/) and an [NHS trust case study (2024)](https://www.hfma.org.uk/system/files/2024-04/Using%20digital%20technologies%20to%20process%20admin%20tasks%20Case%20Study%20v7.pdf) put the staff time to process one referral into the EMR at about 10 to 12 minutes. We haven't measured an "after" time in a deployment, so we don't quote one. To size this for your team, multiply your weekly referrals by those minutes. Referrals that stop still take staff time. The NHS trust's automation also left complex referrals and ones with data problems for staff.

## How the two connect

OpenAdapt runs on a computer you control, or one we host for browser workflows. A run starts from a command, so a desktop flow can launch it with Microsoft's [Run application](https://learn.microsoft.com/en-us/power-automate/desktop-flows/actions-reference/system) action and wait for it to finish. Each run writes a report with its result. OpenAdapt has no Power Automate connector, so your flow's author routes the result, for example by posting stopped runs to Teams.

For each step, ask first whether a connector or an API can make the change, and use it if one can. If the change only happens on screen and a wrong save would land in a patient's chart or a claim, give that step to OpenAdapt and keep the rest in Power Automate.
