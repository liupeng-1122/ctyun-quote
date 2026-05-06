# -*- coding: utf-8 -*-
import sys, os, tempfile
sys.path.insert(0, r'c:\Users\lpcis\WorkBuddy\Ctyun-quote')
from scripts.quote_generator import get_all_products, get_all_hosts, generate_quote_data, get_totals
from scripts.main import create_quote_excel

products = get_all_products()
hosts = get_all_hosts()
print('products:', len(products), 'hosts:', len(hosts))

selected = []
for p in products:
    if p['category'] == '日志审计' and '存储扩容' not in p['name'] and len(selected) < 3:
        selected.append(p)
cloud_hosts = [h for h in hosts if h['id'] in [28, 29, 30]]
selected.extend(cloud_hosts)

quantities = {}
for s in selected:
    quantities[s['id']] = 1
quantities[28] = 2
quantities[29] = 3

data = generate_quote_data(selected, quantities, include_host=True, include_mgmt_host=True)
totals = get_totals(data)

print('quote rows:', len(data))
print('monthly:', totals['monthly'])
print('yearly:', totals['yearly'])
print('discounted:', totals['discounted'])

host_rows = [r for r in data if r.get('is_host')]
print('host rows:', len(host_rows))
for r in host_rows:
    print(' ', r['product'], 'x'+str(r['qty']), 'month='+str(r['monthly']))

out_path = os.path.join(tempfile.gettempdir(), 'test_quote_v19.xlsx')
create_quote_excel(data, totals, out_path, 'test')
print('excel saved:', out_path)
print('size:', os.path.getsize(out_path), 'bytes')
print('ALL TESTS PASSED')
