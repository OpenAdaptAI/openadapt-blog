---
title: "LibreOffice Calc: Annual Asset Changes"
date: 2026-03-01
draft: false
tags: ["recording", "waa", "windows", "libreoffice"]
description: "A 21-step human demonstration of creating a LibreOffice Calc sheet that calculates annual changes for Current Assets, Fixed Assets, and Other Assets from an existing spreadsheet."
---

*From OpenAdapt's earlier research direction; the current product is the workflow compiler — see [openadapt.ai](https://openadapt.ai).*

## Task

Create a new sheet in LibreOffice Calc with 4 headers ("Year", "CA changes", "FA changes", "OA changes"), then calculate the annual changes for each asset column by referencing data on Sheet1 and format the results as percentages.

This recording was made on a Windows VM as part of the [Windows Agent Arena](https://github.com/microsoft/WindowsAgentArena) benchmark evaluation.

## Recording

{{< recording id="04d9aeaf" title="LibreOffice Calc Annual Changes" steps="21" platform="windows" >}}
  {{< recording-step number="1" caption="Right-click on the \"Sheet1\" tab at the bottom and select \"Insert Sheet\" or \"New Sheet\"" src="/recordings/04d9aeaf/step_00.png" >}}
  {{< recording-step number="2" caption="Click cell A1 and type \"Year\"" src="/recordings/04d9aeaf/step_01.png" >}}
  {{< recording-step number="3" caption="Press Tab and type \"CA changes\"" src="/recordings/04d9aeaf/step_02.png" >}}
  {{< recording-step number="4" caption="Press Tab and type \"FA changes\"" src="/recordings/04d9aeaf/step_03.png" >}}
  {{< recording-step number="5" caption="Press Tab and type \"OA changes\"" src="/recordings/04d9aeaf/step_04.png" >}}
  {{< recording-step number="6" caption="Click cell A2 and type \"2015\"" src="/recordings/04d9aeaf/step_05.png" >}}
  {{< recording-step number="7" caption="Press Enter and type \"2016\"" src="/recordings/04d9aeaf/step_06.png" >}}
  {{< recording-step number="8" caption="Press Enter and type \"2017\"" src="/recordings/04d9aeaf/step_07.png" >}}
  {{< recording-step number="9" caption="Press Enter and type \"2018\"" src="/recordings/04d9aeaf/step_08.png" >}}
  {{< recording-step number="10" caption="Press Enter and type \"2019\"" src="/recordings/04d9aeaf/step_09.png" >}}
  {{< recording-step number="11" caption="Click cell B2 and type \"=(Sheet1.B3-Sheet1.B2)/Sheet1.B2\"" src="/recordings/04d9aeaf/step_10.png" >}}
  {{< recording-step number="12" caption="Press Enter" src="/recordings/04d9aeaf/step_11.png" >}}
  {{< recording-step number="13" caption="Click cell B2, then drag the fill handle down to B6" src="/recordings/04d9aeaf/step_12.png" >}}
  {{< recording-step number="14" caption="Click cell C2 and type \"=(Sheet1.C3-Sheet1.C2)/Sheet1.C2\"" src="/recordings/04d9aeaf/step_13.png" >}}
  {{< recording-step number="15" caption="Press Enter" src="/recordings/04d9aeaf/step_14.png" >}}
  {{< recording-step number="16" caption="Click cell C2, then drag the fill handle down to C6" src="/recordings/04d9aeaf/step_15.png" >}}
  {{< recording-step number="17" caption="Click cell D2 and type \"=(Sheet1.D3-Sheet1.D2)/Sheet1.D2\"" src="/recordings/04d9aeaf/step_16.png" >}}
  {{< recording-step number="18" caption="Press Enter" src="/recordings/04d9aeaf/step_17.png" >}}
  {{< recording-step number="19" caption="Click cell D2, then drag the fill handle down to D6" src="/recordings/04d9aeaf/step_18.png" >}}
  {{< recording-step number="20" caption="Click and drag to select cells B2:D6" src="/recordings/04d9aeaf/step_19.png" >}}
  {{< recording-step number="21" caption="Click the % button in the toolbar (or press Ctrl+Shift+5)" src="/recordings/04d9aeaf/step_20.png" >}}
{{< /recording >}}

## Steps

1. Right-click on the "Sheet1" tab at the bottom and select "Insert Sheet" or "New Sheet"
2. Click cell A1 and type "Year"
3. Press Tab and type "CA changes"
4. Press Tab and type "FA changes"
5. Press Tab and type "OA changes"
6. Click cell A2 and type "2015"
7. Press Enter and type "2016"
8. Press Enter and type "2017"
9. Press Enter and type "2018"
10. Press Enter and type "2019"
11. Click cell B2 and type "=(Sheet1.B3-Sheet1.B2)/Sheet1.B2"
12. Press Enter
13. Click cell B2, then drag the fill handle down to B6
14. Click cell C2 and type "=(Sheet1.C3-Sheet1.C2)/Sheet1.C2"
15. Press Enter
16. Click cell C2, then drag the fill handle down to C6
17. Click cell D2 and type "=(Sheet1.D3-Sheet1.D2)/Sheet1.D2"
18. Press Enter
19. Click cell D2, then drag the fill handle down to D6
20. Click and drag to select cells B2:D6
21. Click the % button in the toolbar (or press Ctrl+Shift+5)
