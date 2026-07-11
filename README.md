# AI Stock Radar v3.11.0

AI 股市老師決策工具。

v3.11.0 的重點是 **Responsive Decision UX + Chip Data Foundation**：

- 手機與電腦都以「先看決策」為主。
- 主導覽收斂成：今天怎麼做、今日強勢、我的持股、個股研究、每日報告、設定與資料說明。
- 資料來源、診斷、版本資訊預設收合，避免干擾使用者決策。
- 今日可買、強勢股、持股都以卡片式呈現。
- 籌碼資料基礎版：若 TWSE T86 三大法人資料可取得，會納入每張決策卡；若不可得，明確標示「籌碼資料不足，不納入加分」，不再用量能假裝籌碼。

## 安裝 / 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.11.0_ResponsiveUX_ChipFoundation/upgrade_to_repo.sh
```

## 產生決策資料

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
```

## 啟動 Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 提交

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.11.0 Responsive UX and Chip Data Foundation"
git push
```
