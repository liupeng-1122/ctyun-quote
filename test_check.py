# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import get_all_products, get_all_hosts

hosts = get_all_hosts()
prods = get_all_products()

print('=== 所有云主机 ===')
for h in hosts:
    print(f"  id={h['id']} name={h['name']}")

print('\n=== Web应用防火墙产品（不含云主机类）===')
for p in prods:
    if 'Web应用防火墙' in p['name'] and '云主机' not in p.get('category', ''):
        expected = p['name'] + '-云主机'
        has_host = any(h['name'] == expected for h in hosts)
        print(f"  id={p['id']} name={p['name']} -> 云主机存在:{has_host}")

print('\n=== 日志审计-10资产 ===')
for p in prods:
    if '日志审计-10资产' in p['name']:
        print(f"  id={p['id']} name={p['name']} category={p.get('category','')}")

print('\n=== 管理节点云主机 ===')
for h in hosts:
    if '管理节点' in h['name'] or h['id'] == 69:
        print(f"  id={h['id']} name={h['name']}")
