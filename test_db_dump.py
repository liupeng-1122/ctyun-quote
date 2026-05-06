# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import PRODUCTS, HOSTS

print("=== 当前数据库: PRODUCTS ===")
for p in PRODUCTS:
    print(f"  id={p['id']:>3} | {p['name']}")

print("\n=== 当前数据库: HOSTS ===")
for h in HOSTS:
    print(f"  id={h['id']:>3} | {h['name']}")

print(f"\n产品总数: {len(PRODUCTS)}, 云主机总数: {len(HOSTS)}")
