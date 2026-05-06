# -*- coding: utf-8 -*-
"""V20 修复验证脚本"""
import sys
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import get_all_products, get_all_hosts, get_host_by_id, get_product_by_id, generate_quote_data, get_totals

hosts = get_all_hosts()
prods = get_all_products()

print("=" * 60)
print("V20 修复验证")
print("=" * 60)

# ===== 验证1: Web应用防火墙-独享版-单机版 能匹配到云主机 =====
print("\n[验证1] Web应用防火墙-独享版-单机版 云主机匹配")
prod_waf = None
for p in prods:
    if p['name'] == 'Web应用防火墙-独享版-单机版':
        prod_waf = p
        break

if prod_waf:
    # 模拟 _match_host_for_product 的逻辑
    exact = prod_waf['name'] + '-云主机'
    host_match = None
    for h in hosts:
        if h['name'] == exact:
            host_match = h
            break
    if not host_match:
        # 策略2: 去掉后缀
        suffixes = ['-单机版', '-域名扩展包', '-带宽扩展包', '-业务扩展包', '-规则扩展包']
        for suf in suffixes:
            if prod_waf['name'].endswith(suf):
                base = prod_waf['name'][:-len(suf)]
                expected = base + '-云主机'
                for h in hosts:
                    if h['name'] == expected:
                        host_match = h
                        break
                break
    
    if host_match:
        print(f"  OK! 产品 '{prod_waf['name']}' 匹配到云主机: '{host_match['name']}' (id={host_match['id']})")
    else:
        print(f"  FAIL! 未找到匹配的云主机")
else:
    print("  FAIL! 未找到产品")

# ===== 验证2: 日志审计-10资产 可以正常获取和添加 =====
print("\n[验证2] 日志审计-10资产 产品获取")
prod_log = get_product_by_id(16)
if prod_log:
    print(f"  OK! id={prod_log['id']} name={prod_log['name']} category={prod_log.get('category','')}")
else:
    print("  FAIL! get_product_by_id(16) 返回 None")

# ===== 验证3: 管理节点存在 =====
print("\n[验证3] 管理节点-云主机")
mgmt = get_host_by_id(69)
if mgmt:
    print(f"  OK! id={mgmt['id']} name={mgmt['name']}")
else:
    print("  FAIL! 管理节点不存在")

# ===== 验证4: 完整报价生成（含Web防火墙+日志审计+管理节点）=====
print("\n[验证4] 完整报价生成测试")
selected = []
# 添加 Web应用防火墙-独享版-单机版
if prod_waf:
    selected.append(prod_waf)
# 添加 日志审计-10资产
if prod_log:
    selected.append(prod_log)
# 添加对应云主机
waf_host = None
for h in hosts:
    if h['name'] == 'Web应用防火墙-独享版-云主机':
        waf_host = h
        break
if waf_host:
    selected.append(waf_host)

log_host = get_host_by_id(28)  # 日志审计-10资产-云主机
if log_host:
    selected.append(log_host)

# 添加管理节点
if mgmt:
    selected.append(mgmt)

quantities = {s['id']: 1 for s in selected}
# 设置云主机数量为2
if waf_host:
    quantities[waf_host['id']] = 2
if log_host:
    quantities[log_host['id']] = 3
if mgmt:
    quantities[mgmt['id']] = 1

data = generate_quote_data(selected, quantities, include_host=True, include_mgmt_host=True)
totals = get_totals(data)

print(f"  已选项目: {len(selected)} 个")
print(f"  报价行数: {len(data)} 行")
print(f"  月标准价: {totals['monthly']:.2f}")
print(f"  年标准价: {totals['yearly']:.2f}")
print(f"  折扣价:   {totals['discounted']:.2f}")

# 验证云主机数量
host_rows = [r for r in data if r.get('is_host')]
print(f"\n  云主机行 ({len(host_rows)} 条):")
for r in host_rows:
    print(f"    {r['product']} x{r['qty']} 月={r['monthly']:.0f}")

print("\n" + "=" * 60)
print("全部验证完成!")
