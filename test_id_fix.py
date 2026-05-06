# -*- coding: utf-8 -*-
"""验证修复后的ID冲突逻辑"""
import sys
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import get_product_by_id, get_host_by_id

selected = []

def add_product(prod):
    existing_prod_ids = {p['id'] for p in selected if '云主机' not in p.get('category', '')}
    if prod['id'] not in existing_prod_ids:
        selected.append(prod)
        print(f"  + 产品: {prod['name']} (id={prod['id']})")
        return True
    print(f"  x 产品已存在: {prod['name']} (id={prod['id']})")
    return False

def add_host(host):
    existing_host_ids = {p['id'] for p in selected if '云主机' in p.get('category', '')}
    if host['id'] not in existing_host_ids:
        selected.append(host)
        print(f"  + 云主机: {host['name']} (id={host['id']})")
        return True
    print(f"  x 云主机已存在: {host['name']} (id={host['id']})")
    return False

print("=== 模拟操作序列 ===\n")

# 1. 选产品 日志审计-10资产 (id=16)
add_product(get_product_by_id(16))
# 2. 选产品 下一代防火墙-企业版 (id=17)
add_product(get_product_by_id(17))

# 3. 选云主机 h16 (下一代防火墙-标准版-云主机) - id与产品16冲突!
add_host(get_host_by_id(16))
# 4. 选云主机 h17 (下一代防火墙-高级版-云主机) - id与产品17冲突!
add_host(get_host_by_id(17))
# 5. 选云主机 h28 (日志审计-10资产-云主机)
add_host(get_host_by_id(28))

# 6. 再选一次产品 id=16 (应该显示已存在)
add_product(get_product_by_id(16))
# 7. 再选一次云主机 h16 (应该显示已存在)
add_host(get_host_by_id(16))

print(f"\n最终已选: {len(selected)} 项")
for s in selected:
    typ = '云主机' if '云主机' in s.get('category', '') else '产品'
    print(f"  [{typ}] {s['name']} (id={s['id']})")

expected = 5
if len(selected) == expected:
    print(f"\n=== PASS: 正确添加了{expected}项（产品和云主机互不干扰）===")
else:
    print(f"\n=== FAIL: 预期{expected}项，实际{len(selected)}项 ===")
