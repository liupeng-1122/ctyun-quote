# -*- coding: utf-8 -*-
"""
从 Markdown 报价表解析产品数据，生成 quote_generator.py
"""
import re
import json
import os

def parse_markdown(md_path):
    """解析 Markdown 报价表，返回 products 和 hosts 列表"""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    products = []
    hosts = []
    current_category = ''
    
    for line in lines:
        line = line.strip()
        # 跳过分隔行和表头
        if not line or line.startswith('|---') or line.startswith('| 序号') or line.startswith('|**序号'):
            continue
        # 解析分类标题
        if line.startswith('##'):
            current_category = line.strip('#').strip()
            continue
        if not line.startswith('|'):
            continue
        
        # 分割单元格
        cells = [c.strip() for c in line.split('|')]
        # cells[0] 为空，cells[-1] 也为空
        if len(cells) < 4:
            continue
        
        # 提取数据
        try:
            # Markdown 表格有 12 列，split('|') 后 cells[0] 和 cells[-1] 为空
            # 正确索引：1=序号, 2=规格, 3=规格说明, 4=月价, 5=年价, 6=折扣价, 7=4.5折, 8=5.5折, 9=包年优惠, 10=1年折扣率, 11=3年折扣, 12=备注
            seq_cell = cells[1].strip() if len(cells) > 1 else ''
            spec_cell = cells[2].strip() if len(cells) > 2 else ''
            spec_desc_cell = cells[3].strip() if len(cells) > 3 else ''
            price_month_cell = cells[4].strip() if len(cells) > 4 else '0'
            price_year_cell = cells[5].strip() if len(cells) > 5 else '0'
            discount_price_cell = cells[6].strip() if len(cells) > 6 else '0'
            price_45_cell = cells[7].strip() if len(cells) > 7 else '0'
            price_55_cell = cells[8].strip() if len(cells) > 8 else '0'
            discount_desc_cell = cells[9].strip() if len(cells) > 9 else ''
            disc_rate_cell = cells[10].strip() if len(cells) > 10 else '1'
            remark_cell = cells[12].strip() if len(cells) > 12 else ''
            
            # 跳过序号列的表头
            if not seq_cell.isdigit():
                continue
            
            seq = int(seq_cell)
            
            # 清理价格字符串（移除逗号等）
            def clean_price(s):
                s = s.replace(',', '').replace('，', '').strip()
                if not s or s == '-':
                    return 0
                try:
                    return int(float(s))
                except:
                    return 0
            
            monthly_price = clean_price(price_month_cell)
            yearly_price = clean_price(price_year_cell)
            disc_rate = 1.0
            if disc_rate_cell and disc_rate_cell != '-':
                try:
                    disc_rate = float(disc_rate_cell)
                except:
                    disc_rate = 1.0
            
            # 判断是否为云主机
            is_host = False
            if remark_cell and '合营池云主机费用' in remark_cell:
                is_host = True
            
            entry = {
                "id": seq,
                "category": current_category if current_category else ('云主机' if is_host else '未知'),
                "name": spec_cell,
                "spec": spec_desc_cell,
                "monthly_price": monthly_price,
                "yearly_price": yearly_price,
                "yearly_discount": disc_rate,
                "discount_rate": disc_rate,
                "discount_desc": discount_desc_cell,
                "remark": remark_cell,
                "require_host": False,
                "host_id": None
            }
            
            if is_host:
                hosts.append(entry)
            else:
                products.append(entry)
        except Exception as e:
            print(f"解析失败: {line[:50]}... 错误: {e}")
            continue
    
    return products, hosts

def generate_quote_generator(products, hosts, output_path):
    """生成 quote_generator.py 文件"""
    # 将 products 和 hosts 转换为格式化的 Python 代码
    products_str = json.dumps(products, ensure_ascii=False, indent=4)
    hosts_str = json.dumps(hosts, ensure_ascii=False, indent=4)
    
    # 基础版产品 ID 列表
    basic_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27,
                 35, 36, 37, 38, 39, 40, 41, 42,
                 50, 51, 52, 53, 54,
                 59, 60, 61, 62, 63]
    basic_ids_str = json.dumps(basic_ids, ensure_ascii=False)
    
    # 构建文件内容
    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('"""')
    lines.append('天翼云等保专区报价生成器数据模块')
    lines.append('提供产品、云主机数据以及相关查询、计算、报价生成函数。')
    lines.append('数据来源: 天翼云-云等保专区-安全产品-报价.xlsx')
    lines.append('更新日期: 2026-04-26')
    lines.append('"""')
    lines.append('import copy')
    lines.append('from typing import List, Dict')
    lines.append('')
    lines.append('# ---------------------------------------------------------------------------')
    lines.append('# 数据结构说明')
    lines.append('# 每个产品/主机为字典，关键字段示例：')
    lines.append('# {')
    lines.append('#     "id": 1,')
    lines.append('#     "category": "云安全中心",')
    lines.append('#     "name": "云安全中心-标准版",')
    lines.append('#     "spec": "详细规格说明",')
    lines.append('#     "monthly_price": 1600,')
    lines.append('#     "yearly_price": 19200,')
    lines.append('#     "yearly_discount": 0.85,')
    lines.append('#     "discount_rate": 0.85,')
    lines.append('#     "discount_desc": "包年订购折扣：针对一次性包年付费服务，享受1年及以上8.5折优惠。",')
    lines.append('#     "remark": "",')
    lines.append('#     "require_host": False,')
    lines.append('#     "host_id": None,')
    lines.append('# }')
    lines.append('# ---------------------------------------------------------------------------')
    lines.append('')
    lines.append('# 安全产品列表')
    lines.append('PRODUCTS: List[Dict] = ')
    # 格式化 products_str
    for line in products_str.split('\n'):
        lines.append(line)
    lines.append('')
    lines.append('# 云主机列表')
    lines.append('HOSTS: List[Dict] = ')
    # 格式化 hosts_str
    for line in hosts_str.split('\n'):
        lines.append(line)
    lines.append('')
    lines.append('# 三级等保基础版产品 ID 列表')
    lines.append('BASIC_EDITION_IDS = ')
    for line in basic_ids_str.split('\n'):
        lines.append(line)
    lines.append('')
    lines.append('# ---------------------------------------------------------------------------')
    lines.append('# 基础函数区')
    lines.append('# ---------------------------------------------------------------------------')
    lines.append('')
    lines.append('def get_all_products() -> List[Dict]:')
    lines.append('    """返回所有安全产品（深拷贝）"""')
    lines.append('    return copy.deepcopy(PRODUCTS)')
    lines.append('')
    lines.append('def get_all_hosts() -> List[Dict]:')
    lines.append('    """返回所有云主机（深拷贝）"""')
    lines.append('    return copy.deepcopy(HOSTS)')
    lines.append('')
    lines.append('def get_product_by_id(pid: int) -> Dict:')
    lines.append('    """根据产品 ID 查找产品，未找到返回 None"""')
    lines.append('    for p in PRODUCTS:')
    lines.append('        if p.get("id") == pid:')
    lines.append('            return copy.deepcopy(p)')
    lines.append('    return None')
    lines.append('')
    lines.append('def get_basic_edition_products() -> List[Dict]:')
    lines.append('    """返回三级等保基础版对应的产品子集"""')
    lines.append('    return [copy.deepcopy(p) for p in PRODUCTS if p.get("id") in BASIC_EDITION_IDS]')
    lines.append('')
    lines.append('def calculate_price(product: Dict, quantity: int = 1) -> Dict:')
    lines.append('    """根据数量计算各类价格字段，返回包含计算结果的字典"""')
    lines.append('    qty = max(1, quantity)')
    lines.append('    monthly = product.get("monthly_price", 0) * qty')
    lines.append('    yearly = product.get("yearly_price", 0) * qty')
    lines.append('    # 折扣价使用 yearly_discount')
    lines.append('    discounted = yearly * product.get("yearly_discount", 1)')
    lines.append('    # 4.5 折、5.5 折结算价')
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
    lines.append('def generate_quote_data(selected_products: List[Dict], quantities: Dict[int, int], include_host: bool, include_mgmt_host: bool) -> List[Dict]:')
    lines.append('    """生成用于 Excel 导出的报价数据列表"""')
    lines.append('    data = []')
    lines.append('    for prod in selected_products:')
    lines.append('        pid = prod.get("id")')
    lines.append('        qty = quantities.get(pid, 1)')
    lines.append('        price_info = calculate_price(prod, qty)')
    lines.append('        row = {')
    lines.append('            "seq": pid,')
    lines.append('            "product": prod.get("name"),')
    lines.append('            "spec": prod.get("spec"),')
    lines.append('            "qty": qty,')
    lines.append('            "monthly": price_info["monthly"],')
    lines.append('            "yearly": price_info["yearly"],')
    lines.append('            "discounted": price_info["discounted"],')
    lines.append('            "price_45": price_info["price_45"],')
    lines.append('            "price_55": price_info["price_55"],')
    lines.append('            "discount_desc": prod.get("discount_desc", ""),')
    lines.append('            "remark": prod.get("remark", ""),')
    lines.append('            "is_host": False,')
    lines.append('        }')
    lines.append('        data.append(row)')
    lines.append('    # 云主机（合营池）处理')
    lines.append('    if include_host:')
    lines.append('        for host in HOSTS:')
    lines.append('            pid = host.get("id")')
    lines.append('            qty = quantities.get(pid, 1)')
    lines.append('            price_info = calculate_price(host, qty)')
    lines.append('            row = {')
    lines.append('                "seq": pid,')
    lines.append('                "product": host.get("name"),')
    lines.append('                "spec": host.get("spec"),')
    lines.append('                "qty": qty,')
    lines.append('                "monthly": price_info["monthly"],')
    lines.append('                "yearly": price_info["yearly"],')
    lines.append('                "discounted": price_info["discounted"],')
    lines.append('                "price_45": price_info["price_45"],')
    lines.append('                "price_55": price_info["price_55"],')
    lines.append('                "discount_desc": host.get("discount_desc", ""),')
    lines.append('                "remark": host.get("remark", ""),')
    lines.append('                "is_host": True,')
    lines.append('            }')
    lines.append('            data.append(row)')
    lines.append('    return data')
    lines.append('')
    lines.append('def get_totals(data: List[Dict]) -> Dict[str, float]:')
    lines.append('    """汇总所有行的金额字段，返回字典"""')
    lines.append('    totals = {')
    lines.append('        "monthly": 0.0,')
    lines.append('        "yearly": 0.0,')
    lines.append('        "discounted": 0.0,')
    lines.append('        "price_45": 0.0,')
    lines.append('        "price_55": 0.0,')
    lines.append('    }')
    lines.append('    for row in data:')
    lines.append('        totals["monthly"] += float(row.get("monthly", 0))')
    lines.append('        totals["yearly"] += float(row.get("yearly", 0))')
    lines.append('        totals["discounted"] += float(row.get("discounted", 0))')
    lines.append('        totals["price_45"] += float(row.get("price_45", 0))')
    lines.append('        totals["price_55"] += float(row.get("price_55", 0))')
    lines.append('    return totals')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"已生成 {output_path}")
    print(f"产品数量: {len(products)}")
    print(f"云主机数量: {len(hosts)}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, '..', 'knowledge-base', 'inbox', '天翼云等保专区安全产品报价表.md')
    output_path = os.path.join(script_dir, 'quote_generator.py')
    products, hosts = parse_markdown(md_path)
    generate_quote_generator(products, hosts, output_path)
