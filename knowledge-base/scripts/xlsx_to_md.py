import sys
import pandas as pd
from pathlib import Path

xlsx_path = r"C:\Users\lpcis\Documents\我的知识库\天翼云-云等保专区-安全产品-报价.xlsx"
out_path = r"C:\Users\lpcis\WorkBuddy\20260425192322\knowledge-base\inbox\天翼云等保专区安全产品报价表.md"

df = pd.read_excel(xlsx_path, sheet_name="等保专区报价表")

valid = df[df["序号"].apply(lambda x: str(x).strip().isdigit() if pd.notna(x) else False)].copy()

lines = []
lines.append("# 天翼云等保专区 - 安全产品报价表")
lines.append("")
lines.append("> 数据来源: 天翼云-云等保专区-安全产品-报价.xlsx")
lines.append("> 更新日期: 2026-04-26")
lines.append("")

for pname, grp in valid.groupby("产品名称", sort=False):
    lines.append("## " + str(pname))
    lines.append("")
    lines.append("| 序号 | 规格 | 规格说明 | 标准价格(元/月) | 标准价格(元/年) | 1年包年折扣价 | 1年4.5折结算价 | 1年5.5折结算价 | 包年优惠 | 1年折扣率 | 3年折扣 | 备注 |")
    lines.append("|------|------|----------|---------------|---------------|-------------|--------------|--------------|---------|----------|--------|------|")
    for _, row in grp.iterrows():
        seq = int(float(row["序号"]))
        spec = str(row["规格"]) if pd.notna(row["规格"]) else ""
        desc = str(row["规格说明"]).replace("\n", " ") if pd.notna(row["规格说明"]) else ""
        mp = row["标准价格（元/月）"]
        yp = row["标准价格（元/年）"]
        d1 = row["1年包年折扣价"]
        d45 = row["1年4.5折结算折扣价"]
        d55 = row["1年5.5折结算折扣价"]
        promo = str(row["包年优惠"]).replace("\n", " ") if pd.notna(row["包年优惠"]) else ""
        rate1 = str(row["1年包年折扣率"]) if pd.notna(row["1年包年折扣率"]) else ""
        rate3 = str(row["3年包年折扣"]) if pd.notna(row["3年包年折扣"]) else ""
        note = str(row["备注"]) if pd.notna(row["备注"]) else ""

        month_price = "{:,.0f}".format(mp) if pd.notna(mp) else ""
        year_price = "{:,.0f}".format(yp) if pd.notna(yp) else ""
        disc1 = "{:,.0f}".format(d1) if pd.notna(d1) else ""
        disc45 = "{:,.0f}".format(d45) if pd.notna(d45) else ""
        disc55 = "{:,.0f}".format(d55) if pd.notna(d55) else ""

        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            seq, spec, desc, month_price, year_price, disc1, disc45, disc55, promo, rate1, rate3, note))
    lines.append("")

# Totals
total_row = df[df["序号"] == "合计"]
if not total_row.empty:
    t = total_row.iloc[0]
    lines.append("## 合计")
    lines.append("")
    lines.append("- 标准价格(元/月): {:,.1f}".format(t["标准价格（元/月）"]))
    lines.append("- 标准价格(元/年): {:,.1f}".format(t["标准价格（元/年）"]))
    lines.append("- 1年包年折扣价: {:,.1f}".format(t["1年包年折扣价"]))
    lines.append("- 1年4.5折结算折扣价: {:,.0f}".format(t["1年4.5折结算折扣价"]))
    lines.append("- 1年5.5折结算折扣价: {:,.0f}".format(t["1年5.5折结算折扣价"]))
    lines.append("")

# Notes
note_row = df[df["序号"].astype(str).str.contains("服务商", na=False)]
if not note_row.empty:
    lines.append("## 注意事项")
    lines.append("")
    note_text = str(note_row.iloc[0]["序号"]).replace("\\n", "\n")
    for nl in note_text.split("\n"):
        lines.append("- " + nl)
    lines.append("")

md = "\n".join(lines)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(md)
print("Done: " + out_path)
print("Lines: " + str(len(lines)))
