# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import get_all_products, get_all_hosts, get_host_by_id

hosts = get_all_hosts()
prods = get_all_products()

print("=== 下一代防火墙相关 ===")
for p in prods:
    if '下一代防火墙' in p['name'] and '云主机' not in p.get('category', ''):
        print(f"  产品: id={p['id']} name={p['name']}")

print("\n=== 下一代防火墙相关云主机 ===")
for h in hosts:
    if '下一代防火墙' in h['name']:
        print(f"  云主机: id={h['id']} name={h['name']}")

print("\n=== get_host_by_id 测试 ===")
for hid in [16, 17, 18]:
    h = get_host_by_id(hid)
    if h:
        print(f"  get_host_by_id({hid}) -> {h['name']} (type ok)")
    else:
        print(f"  get_host_by_id({hid}) -> None !!!")

print("\n=== ID冲突检查 ===")
prod_ids = {p['id'] for p in prods}
host_ids = {h['id'] for h in hosts}
conflicts = prod_ids & host_ids
if conflicts:
    print(f"  ID冲突: {sorted(conflicts)}")
    for cid in sorted(conflicts):
        pname = [p['name'] for p in prods if p['id'] == cid]
        hname = [h['name'] for h in hosts if h['id'] == cid]
        print(f"    id={cid}: 产品={pname} / 云主机={hname}")
else:
    print("  无ID冲突")
