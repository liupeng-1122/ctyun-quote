# -*- coding: utf-8 -*-
"""验证: 选13项生成13行（不再自动追加全部云主机）"""
import sys
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import get_all_products, get_all_hosts, get_product_by_id, get_host_by_id, generate_quote_data, get_totals

# 模拟用户的13个已选项（和截图中一致）
selected = []

# 安全产品
for pid in [11, 4, 10]:  # 云安全中心-标准版, 主机安全-旗舰版, Web应用防火墙-独享版-单机版
    p = get_product_by_id(pid)
    if p:
        selected.append(p)

# 日志审计产品 + 其云主机
p_log = get_product_by_id(16)  # 日志审计-10资产
if p_log:
    selected.append(p_log)
h_waf = get_host_by_id(13)  # Web应用防火墙-独享版-云主机
if h_waf:
    selected.append(h_waf)
h_log = get_host_by_id(28)  # 日志审计-10资产-云主机
if h_log:
    selected.append(h_log)

# 堡垒机
for pid in [35]:
    p = get_product_by_id(pid)
    if p:
        selected.append(p)
h_bf = get_host_by_id(43)  # 堡垒机-10资产-云主机
if h_bf:
    selected.append(h_bf)

# 数据库审计
for pid in [50]:
    p = get_product_by_id(pid)
    if p:
        selected.append(p)
h_db4 = get_host_by_id(58)  # 数据库审计-4资产-云主机
if h_db4:
    selected.append(h_db4)

# 漏洞扫描
for pid in [59]:
    p = get_product_by_id(pid)
    if p:
        selected.append(p)
h_ls = get_host_by_id(64)  # 漏洞扫描-10资产-云主机
if h_ls:
    selected.append(h_ls)

# 管理节点
mgmt = get_host_by_id(69)
if mgmt:
    selected.append(mgmt)

# 设置数量（数据库审计云主机x5）
quantities = {s['id']: 1 for s in selected}
quantities[58] = 5  # 数据库审计-4资产-云主机 x5

print(f"已选项目数: {len(selected)}")
for s in selected:
    typ = "云主机" if "云主机" in s.get("category", "") else "产品"
    print(f"  [{typ}] {s['name']} (id={s['id']})")

# 用 include_host=False（修复后的调用方式）
data = generate_quote_data(selected, quantities, include_host=False, include_mgmt_host=False)
totals = get_totals(data)

print(f"\n生成的报价行数: {len(data)}")
print(f"月价: {totals['monthly']:.2f}")
print(f"年价: {totals['yearly']:.2f}")

if len(data) == len(selected):
    print(f"\n=== PASS: 已选{len(selected)}项 -> 生成{len(data)}行 ===")
else:
    print(f"\n=== FAIL: 已选{len(selected)}项 但生成{len(data)}行! ===")
