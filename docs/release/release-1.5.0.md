# Release Notes - v1.5.0 Teacher Buy List

## Goal

Deliver a practical daily teacher-style buy list.

The key question this release answers:

> 哪些股票今天已具備波段可操作條件？

## User Value

The user no longer needs to infer from many cards and charts. The product now leads with:

1. 今日可買進名單
2. 等級 A/B/C/D
3. 買點類型
4. 進場區間
5. 突破價
6. 停損 / 失效價
7. 第一與第二停利價
8. 不追高原則

## Validation

Run:

```bash
PYTHONPATH=src python3 -m radar.cli run
```

Then open Dashboard:

```bash
PYTHONPATH=src python3 -m streamlit run app.py
```
