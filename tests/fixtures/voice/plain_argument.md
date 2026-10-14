---
title: "Count the saves you didn't check"
date: 2026-04-14
author: "Test Fixture"
description: "Most automation reports count finished runs. Here's how to count the runs that finished without anyone confirming the saved data."
thesis: "A success rate that counts finished runs hides the runs that saved the wrong data, so count checked saves separately."
audience: practitioner
post_type: essay
---

Most automation dashboards report one number: the share of runs that finished. I think that number is misleading for any task that writes data, and I'd like you to try a different count before you trust it.

## What the usual number counts

A run finishes when the script reaches its last step without an error. That tells you the clicks happened. It doesn't tell you whether the record you meant to change now holds the right values. If a form silently drops a field, or the server rejects the save after the page says "Saved", the run still finishes and still adds to the success rate.

We learned this the slow way. In March, one of our scheduled jobs reported 100 percent success for 9 days while about 1 in 20 entries landed with an empty date field. Nobody was careless. The report simply had no column for it.

## A second count

Split your runs into three groups: finished and checked, finished but not checked, and stopped. A checked run is one where something other than the script read the saved record back and compared it with what was entered. Most teams will find the middle group is the largest, and that's fine as a starting point. The goal is to see it.

Checking every field on every run is expensive, so start with the fields that cost the most when they're wrong. For a referral that's usually the patient, the date, and the referring provider. A read-back of three fields is cheap compared with a denied claim.

## What changes when you track it

Once the middle group has a number, people start asking why it's so large, which is the right question. In our case the answer was that two of our systems had no easy way to read a record back. We wrote a small export for one of them and asked the vendor about the other.

The stopped group deserves attention too. A run that stops before saving has done its job if it stopped for a good reason. Track why each one stopped, rather than counting all of them as failures, and you'll find most of them point at the same two or three screens.

If you run automations that write data, add the second count to your next weekly report and see how the numbers compare.
