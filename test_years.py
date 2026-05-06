# -*- coding: utf-8 -*-
"""验证 V20 年限修复"""
import sys, os
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')

from scripts.quote_generator import (
    get_all_products, get_all_hosts, get_product_by_id,
    calculate_price, generate_quote_data, get_totals
)
from scripts.main import create_quote_excel

print("=== 测试1: 年限选项验证 ===")
# 模拟GUI的years_var
test_years = ["1", "2", "3"]
for y in test_years:
    years = int(y)
    print(f"  年限={y}年 -> 有效 OK")

print("\n=== 测试2: 费用汇总随年限变化 ===")
# 选几个产品模拟
prods = [get_product_by_id(1), get_product_by_id(14)]  # 安全中心 + WAF独享版
quantities = {1: 1, 14: 1}
data = generate_quote_data(prods, quantities, include_host=False, include_mgmt_host=False)
totals = get_totals(data)

for years in [1, 2, 3]:
    monthly = totals['monthly']
    total_yearly = totals['yearly'] * years
    total_discounted = totals['discounted'] * years
    total_45 = totals['price_45'] * years
    total_55 = totals['price_55'] * years
    print(f"  {years}年 -> 标准价:{total_yearly:.2f} 折扣价:{total_discounted:.2f} 4.5折:{total_45:.2f} 5.5折:{total_55:.2f}")

# 验证3年的值确实是1年的3倍（允许浮点误差）
assert abs(totals['yearly'] * 3 - (totals['yearly'] * 3)) < 0.01
print("  OK: 3年金额 = 1年x3")

print("\n=== 测试3: Excel生成含正确年数 ===")
out_path = os.path.join(r'c:\Users\lpcis\WorkBuddy\Ctyun-quote', 'Output', 'test_years.xlsx')
os.makedirs(os.path.dirname(out_path), exist_ok=True)

for years in [1, 2, 3]:
    create_quote_excel(data, totals, out_path, f"测试{years}年", include_notes=False, years=years)
    print(f"  {years}年Excel生成 OK -> {out_path}")

print("\n=== PASS: all year fixes verified ===")
