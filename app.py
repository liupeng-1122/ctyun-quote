# -*- coding: utf-8 -*-
"""
天翼云等保专区报价系统 - Flask Web 版
为 Android APK 封装备用的网页服务端
"""

import os
import sys
import io
import tempfile
from datetime import datetime

from flask import Flask, jsonify, request, render_template, send_file

# 复用现有业务模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scripts.quote_generator import (
    get_all_products, get_all_hosts, get_product_by_id,
    calculate_price, generate_quote_data, get_totals,
)
from scripts.main import create_quote_excel

app = Flask(__name__)

# ============================================================
# API：获取全部分类产品和云主机
# ============================================================
@app.route('/api/products')
def api_products():
    products = get_all_products()
    hosts = get_all_hosts()
    # 按 category 分组
    categories = {}
    for p in products:
        cat = p['category']
        categories.setdefault(cat, []).append({
            'id': p['id'],
            'name': p['name'],
            'spec': p['spec'],
            'monthly_price': p['monthly_price'],
            'yearly_price': p['yearly_price'],
            'discount_desc': p['discount_desc'],
            'remark': p['remark'],
        })
    # 云主机分组
    host_categories = {}
    for h in hosts:
        cat = h['category']
        host_categories.setdefault(cat, []).append({
            'id': h['id'],
            'name': h['name'],
            'spec': h['spec'],
            'monthly_price': h['monthly_price'],
            'yearly_price': h['yearly_price'],
            'discount_desc': h['discount_desc'],
            'remark': h['remark'],
        })
    return jsonify({
        'categories': categories,
        'hostCategories': host_categories,
    })


# ============================================================
# API：计算报价
# ============================================================
@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.get_json(force=True)
    items = data.get('items', [])       # [{id, qty}]
    years = int(data.get('years', 1))

    products = get_all_products()
    hosts = get_all_hosts()
    all_items = products + hosts
    product_map = {p['id']: p for p in all_items}

    selected = []
    quantities = {}
    for item in items:
        pid = item['id']
        qty = item.get('qty', 1)
        prod = product_map.get(pid)
        if prod:
            selected.append(prod)
            quantities[pid] = qty

    if not selected:
        return jsonify({'error': '未选择产品'}), 400

    quote_items = []
    for prod in selected:
        pid = prod['id']
        qty = quantities.get(pid, 1)
        prices = calculate_price(prod, qty)
        quote_items.append({
            'id': pid,
            'name': prod['name'],
            'spec': prod['spec'],
            'qty': qty,
            'monthly': prices['monthly'],
            'yearly': prices['yearly'],
            'discounted': prices['discounted'],
            'price_45': prices['price_45'],
            'price_55': prices['price_55'],
            'discount_desc': prod.get('discount_desc', ''),
            'remark': prod.get('remark', ''),
            'isHost': '云主机' in prod.get('category', ''),
        })

    totals = get_totals(quote_items)

    return jsonify({
        'items': quote_items,
        'count': len(quote_items),
        'totals': {
            'monthly': round(totals['monthly'], 2),
            'yearly': round(totals['yearly'], 2),
            'yearlyTotal': round(totals['yearly'] * years, 2),
            'discounted': round(totals['discounted'], 2),
            'discountedTotal': round(totals['discounted'] * years, 2),
            'price_45': round(totals['price_45'] * years, 2),
            'price_55': round(totals['price_55'] * years, 2),
        },
        'years': years,
    })


# ============================================================
# API：生成并下载 Excel 报价表
# ============================================================
@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json(force=True)
    items = data.get('items', [])
    years = int(data.get('years', 1))

    products = get_all_products()
    hosts = get_all_hosts()
    all_items = products + hosts
    product_map = {p['id']: p for p in all_items}

    selected = []
    quantities = {}
    for item in items:
        pid = item['id']
        qty = item.get('qty', 1)
        prod = product_map.get(pid)
        if prod:
            selected.append(prod)
            quantities[pid] = qty

    if not selected:
        return jsonify({'error': '未选择产品'}), 400

    # 生成报价数据
    quote_data = []
    for prod in selected:
        pid = prod['id']
        qty = quantities.get(pid, 1)
        prices = calculate_price(prod, qty)
        quote_data.append({
            'seq': pid,
            'product': prod['name'],
            'spec': prod['spec'],
            'qty': qty,
            'monthly': prices['monthly'],
            'yearly': prices['yearly'],
            'discounted': prices['discounted'],
            'price_45': prices['price_45'],
            'price_55': prices['price_55'],
            'discount_desc': prod.get('discount_desc', ''),
            'remark': prod.get('remark', ''),
            'is_host': '云主机' in prod.get('category', ''),
        })

    totals = get_totals(quote_data)

    # 生成 Excel 到临时文件
    tmp_dir = tempfile.mkdtemp()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'天翼云等保专区安全产品报价表_{timestamp}.xlsx'
    output_path = os.path.join(tmp_dir, filename)

    create_quote_excel(
        quote_data, totals, output_path,
        title='天翼云等保专区安全产品报价表（手机版）',
        years=years,
    )

    return send_file(
        output_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


# ============================================================
# 主页面
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')


# ============================================================
# 启动入口
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', '0') == '1'
    print(f"🌐 天翼云等保报价系统启动中... http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)