# -*- coding: utf-8 -*-
"""
直接生成有效的 Python 代码，不依赖 json.dumps() 输出
手动格式化字典，确保 Python 语法正确
"""
import os


def parse_md(md_path):
    products = []
    hosts = []
    category = ''

    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if line.startswith('|---'):
                continue
            if '| 序号 ' in line or '|序号' in line:
                continue
            if line.startswith('##'):
                category = line.replace('##', '').strip()
                continue
            if not line.startswith('|'):
                continue

            parts = line.split('|')
            if len(parts) < 14:
                continue

            try:
                seq_str = parts[1].strip()
                if not seq_str.isdigit():
                    continue
                seq = int(seq_str)

                name = parts[2].strip()
                spec_parts = [p.strip() for p in parts[3:-10] if p.strip()]
                spec = ' | '.join(spec_parts)

                monthly = parts[-10].strip()
                yearly = parts[-9].strip()
                discounted = parts[-8].strip()
                price_45 = parts[-7].strip()
                price_55 = parts[-6].strip()
                discount_desc = parts[-5].strip()
                disc_rate_str = parts[-4].strip()
                _ = parts[-3].strip()
                remark = parts[-2].strip()

                def clean(s):
                    s = s.replace(',', '').replace('，', '').strip()
                    if not s or s == '-':
                        return 0
                    try:
                        return int(float(s))
                    except:
                        return 0

                monthly_price = clean(monthly)
                yearly_price = clean(yearly)

                disc_rate = 1.0
                if disc_rate_str and disc_rate_str != '-':
                    try:
                        disc_rate = float(disc_rate_str)
                    except:
                        pass

                is_host = '合营池云主机费用' in remark

                entry = {
                    "id": seq,
                    "category": category if category else ('云主机' if is_host else '未知'),
                    "name": name,
                    "spec": spec,
                    "monthly_price": monthly_price,
                    "yearly_price": yearly_price,
                    "yearly_discount": disc_rate,
                    "discount_rate": disc_rate,
                    "discount_desc": discount_desc,
                    "remark": remark,
                    "require_host": False,
                    "host_id": None
                }

                if is_host:
                    hosts.append(entry)
                else:
                    products.append(entry)
            except Exception as e:
                print(f"跳过行，错误: {e}")
                continue

    return products, hosts


def fmt_str(s):
    """将字符串转义并包裹引号（兼容 Python repr）"""
    # 简单的 JSON 风格字符串化，再做 Python 兼容性处理
    escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
    return f'"{escaped}"'


def fmt_dict(d, indent=4):
    """手动格式化单个字典为 Python 语法字符串"""
    spaces = ' ' * indent
    inner_spaces = ' ' * (indent + 4)
    parts = []
    for k, v in d.items():
        key_str = f'"{k}"'
        if v is None:
            val_str = 'None'
        elif isinstance(v, bool):
            val_str = 'True' if v else 'False'
        elif isinstance(v, (int, float)):
            val_str = repr(v)
        elif isinstance(v, str):
            val_str = fmt_str(v)
        else:
            val_str = repr(v)
        parts.append(f'{inner_spaces}{key_str}: {val_str}')
    return '{\n' + ',\n'.join(parts) + ',\n' + spaces + '}'


def gen_quote_generator(products, hosts, out_path):
    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('"""')
    lines.append('天翼云等保专区报价生成器数据模块')
    lines.append('数据来源: 天翼云等保专区安全产品报价表.md')
    lines.append('更新日期: 2026-04-27')
    lines.append('"""')
    lines.append('import copy')
    lines.append('from typing import List, Dict')
    lines.append('')
    lines.append('# 安全产品列表')
    lines.append('PRODUCTS: List[Dict] = [')

    for p in products:
        dict_str = fmt_dict(p, indent=4)
        lines.append(dict_str + ',')

    lines.append(']')
    lines.append('')
    lines.append('# 云主机列表')
    lines.append('HOSTS: List[Dict] = [')

    for h in hosts:
        dict_str = fmt_dict(h, indent=4)
        lines.append(dict_str + ',')

    lines.append(']')
    lines.append('')
    lines.append('# 三级等保基础版产品 ID 列表')
    lines.append('BASIC_EDITION_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27,')
    lines.append('                 35, 36, 37, 38, 39, 40, 41, 42,')
    lines.append('                 50, 51, 52, 53, 54,')
    lines.append('                 59, 60, 61, 62, 63]')
    lines.append('')
    lines.append('')
    lines.append('def get_all_products() -> List[Dict]:')
    lines.append('    return copy.deepcopy(PRODUCTS)')
    lines.append('')
    lines.append('def get_all_hosts() -> List[Dict]:')
    lines.append('    return copy.deepcopy(HOSTS)')
    lines.append('')
    lines.append('def get_product_by_id(pid: int) -> Dict:')
    lines.append('    for p in PRODUCTS:')
    lines.append('        if p.get("id") == pid:')
    lines.append('            return copy.deepcopy(p)')
    lines.append('    return None')
    lines.append('')
    lines.append('def get_basic_edition_products() -> List[Dict]:')
    lines.append('    return [copy.deepcopy(p) for p in PRODUCTS if p.get("id") in BASIC_EDITION_IDS]')
    lines.append('')
    lines.append('def calculate_price(product: Dict, quantity: int = 1) -> Dict:')
    lines.append('    qty = max(1, quantity)')
    lines.append('    monthly = product.get("monthly_price", 0) * qty')
    lines.append('    yearly = product.get("yearly_price", 0) * qty')
    lines.append('    discounted = yearly * product.get("yearly_discount", 1)')
    lines.append('    price_45 = discounted * 0.45')
    lines.append('    price_55 = discounted * 0.55')
    lines.append('    return {')
    lines.append('        "monthly": monthly,')
    lines.append('        "yearly": yearly,')
    lines.append('        "discounted": discounted,')
    lines.append('        "price_45": price_45,')
    lines.append('        "price_55": price_55,')
    lines.append('    }')
    lines.append('')
    lines.append('def generate_quote_data(selected_products, quantities, include_host, include_mgmt_host):')
    lines.append('    data = []')
    lines.append('    for prod in selected_products:')
    lines.append('        pid = prod.get("id")')
    lines.append('        qty = quantities.get(pid, 1)')
    lines.append('        price_info = calculate_price(prod, qty)')
    lines.append('        row = {')
    lines.append('            "seq": pid, "product": prod.get("name"), "spec": prod.get("spec"),')
    lines.append('            "qty": qty, "monthly": price_info["monthly"], "yearly": price_info["yearly"],')
    lines.append('            "discounted": price_info["discounted"], "price_45": price_info["price_45"],')
    lines.append('            "price_55": price_info["price_55"], "discount_desc": prod.get("discount_desc", ""),')
    lines.append('            "remark": prod.get("remark", ""), "is_host": False,')
    lines.append('        }')
    lines.append('        data.append(row)')
    lines.append('    if include_host:')
    lines.append('        for host in HOSTS:')
    lines.append('            pid = host.get("id")')
    lines.append('            qty = quantities.get(pid, 1)')
    lines.append('            price_info = calculate_price(host, qty)')
    lines.append('            row = {')
    lines.append('                "seq": pid, "product": host.get("name"), "spec": host.get("spec"),')
    lines.append('                "qty": qty, "monthly": price_info["monthly"], "yearly": price_info["yearly"],')
    lines.append('                "discounted": price_info["discounted"], "price_45": price_info["price_45"],')
    lines.append('                "price_55": price_info["price_55"], "discount_desc": host.get("discount_desc", ""),')
    lines.append('                "remark": host.get("remark", ""), "is_host": True,')
    lines.append('            }')
    lines.append('            data.append(row)')
    lines.append('    return data')
    lines.append('')
    lines.append('def get_totals(data):')
    lines.append('    totals = {"monthly": 0.0, "yearly": 0.0, "discounted": 0.0, "price_45": 0.0, "price_55": 0.0}')
    lines.append('    for row in data:')
    lines.append('        totals["monthly"] += float(row.get("monthly", 0))')
    lines.append('        totals["yearly"] += float(row.get("yearly", 0))')
    lines.append('        totals["discounted"] += float(row.get("discounted", 0))')
    lines.append('        totals["price_45"] += float(row.get("price_45", 0))')
    lines.append('        totals["price_55"] += float(row.get("price_55", 0))')
    lines.append('    return totals')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"已生成: {out_path}")
    print(f"产品数: {len(products)}, 云主机数: {len(hosts)}")


if __name__ == '__main__':
    base = os.path.dirname(os.path.abspath(__file__))
    md = os.path.join(base, '..', 'knowledge-base', 'inbox', '天翼云等保专区安全产品报价表.md')
    out = os.path.join(base, 'quote_generator.py')
    products, hosts = parse_md(md)
    gen_quote_generator(products, hosts, out)
