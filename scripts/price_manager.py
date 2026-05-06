# -*- coding: utf-8 -*-
"""
天翼云等保专区报价数据管理工具
功能：
- 查看、编辑安全产品和云主机的价格、规格、折扣等信息
- 从知识库 Markdown 报价表导入最新数据
- 导出为 JSON 备份文件
- 保存修改后自动同步回 `scripts/quote_generator.py`
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ast
import copy

# 项目根目录（确保可以导入 quote_generator）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.quote_generator import PRODUCTS as ORIGINAL_PRODUCTS, HOSTS as ORIGINAL_HOSTS


# ------------------- 数据加载与保存 -------------------

def load_data():
    """返回可编辑的深拷贝列表"""
    return copy.deepcopy(ORIGINAL_PRODUCTS), copy.deepcopy(ORIGINAL_HOSTS)


def _find_matching_bracket(text, start_pos):
    """从 start_pos (指向 '[') 开始，找到匹配的 ']' 位置"""
    if text[start_pos] != '[':
        return -1
    stack = 1
    pos = start_pos + 1
    while pos < len(text) and stack > 0:
        ch = text[pos]
        if ch == '[':
            stack += 1
        elif ch == ']':
            stack -= 1
        pos += 1
    if stack == 0:
        return pos - 1  # 返回匹配的 ']' 位置
    return -1


def _replace_var_with_ast(content, var_name, new_value_str):
    """使用 AST 定位变量赋值范围并替换为新值"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    # 精确定位赋值语句的字节范围
                    lines = content.splitlines(keepends=True)
                    start_offset = 0
                    for i in range(node.lineno - 1):
                        start_offset += len(lines[i])
                    end_offset = 0
                    for i in range(node.end_lineno):
                        end_offset += len(lines[i])
                    # 替换
                    new_content = content[:start_offset] + f'{var_name} = ' + new_value_str + content[end_offset:]
                    return new_content
    return None


def _recalc_product(p):
    """根据月价和折扣自动计算年价及结算价"""
    mp = p.get('monthly_price', 0)
    # 1年
    dr1 = p.get('discount_rate', 1.0)
    p['yearly_price'] = int(mp * 12 * dr1)
    # 结算价 4.5折、5.5折
    p['price_45'] = int(p['yearly_price'] * 0.45)
    p['price_55'] = int(p['yearly_price'] * 0.55)
    # 2年折扣
    dr2 = p.get('discount_2y', dr1)
    p['yearly_price_2y'] = int(mp * 24 * dr2)
    p['price_45_2y'] = int(p['yearly_price_2y'] * 0.45)
    p['price_55_2y'] = int(p['yearly_price_2y'] * 0.55)
    # 3年折扣
    dr3 = p.get('discount_3y', dr1)
    p['yearly_price_3y'] = int(mp * 36 * dr3)
    p['price_45_3y'] = int(p['yearly_price_3y'] * 0.45)
    p['price_55_3y'] = int(p['yearly_price_3y'] * 0.55)
    return p

def save_to_quote_generator(products, hosts):
    """将修改后的 PRODUCTS、HOSTS 列表写回 quote_generator.py（使用 AST 精确定位）"""
    # 自动计算价格字段
    products = [_recalc_product(p) for p in products]
    file_path = os.path.join(BASE_DIR, 'scripts', 'quote_generator.py')
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    prod_str = json.dumps(products, ensure_ascii=False, indent=4)
    host_str = json.dumps(hosts, ensure_ascii=False, indent=4)

    # 替换 PRODUCTS
    new_content = _replace_var_with_ast(content, 'PRODUCTS', prod_str)
    if new_content is None:
        messagebox.showerror('保存失败', '无法定位 PRODUCTS 变量，请检查 quote_generator.py 格式')
        return
    # 替换 HOSTS（在已更新的内容中）
    newer_content = _replace_var_with_ast(new_content, 'HOSTS', host_str)
    if newer_content is None:
        messagebox.showerror('保存失败', '无法定位 HOSTS 变量，请检查 quote_generator.py 格式')
        return

    # 同时更新 BASIC_EDITION_PRODUCTS（固定列表，直接替换为 products 的子集）
    basic_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27,
                 35, 36, 37, 38, 39, 40, 41, 42,
                 50, 51, 52, 53, 54,
                 59, 60, 61, 62, 63]
    basic_products = [p for p in products if p.get('id') in basic_ids]
    basic_str = json.dumps(basic_products, ensure_ascii=False, indent=4)
    newest_content = _replace_var_with_ast(newer_content, 'BASIC_EDITION_PRODUCTS', basic_str)
    if newest_content is None:
        messagebox.showerror('保存失败', '无法定位 BASIC_EDITION_PRODUCTS 变量，请检查 quote_generator.py 格式')
        return

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(newest_content)

    messagebox.showinfo('保存成功', '已同步至 quote_generator.py')


def import_from_markdown(md_path):
    """解析知识库报价表的 Markdown，返回 products、hosts 两个列表"""
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

        # 尝试提取数据
        try:
            seq_cell = cells[1]
            spec_cell = cells[2] if len(cells) > 2 else ''
            spec_desc_cell = cells[3] if len(cells) > 3 else ''
            price_month_cell = cells[4] if len(cells) > 4 else '0'
            price_year_cell = cells[5] if len(cells) > 5 else '0'
            discount_price_cell = cells[6] if len(cells) > 6 else '0'
            price_45_cell = cells[7] if len(cells) > 7 else '0'
            price_55_cell = cells[8] if len(cells) > 8 else '0'
            remark_cell = cells[9] if len(cells) > 9 else ''
            disc_rate_cell = cells[10] if len(cells) > 10 else '1'
            extra_cell = cells[12] if len(cells) > 12 else ''

            # 跳过序号列的表头
            if not seq_cell.isdigit():
                continue

            seq = int(seq_cell)
            monthly_price = int(price_month_cell.replace(',', '').replace('，', ''))
            yearly_price = int(price_year_cell.replace(',', '').replace('，', ''))
            disc_rate = float(disc_rate_cell) if disc_rate_cell else 1.0

            # 判断是否为云主机
            is_host = '云主机' in remark_cell or '云主机' in spec_cell or '云主机' in spec_desc_cell

            entry = {
                "id": seq,
                "category": current_category if current_category else ('云主机' if is_host else '未知'),
                "name": spec_cell,
                "spec": spec_desc_cell,
                "monthly_price": monthly_price,
                "yearly_price": yearly_price,
                "yearly_discount": disc_rate,
                "discount_rate": disc_rate,
                "discount_2y": disc_rate,  # 默认与一年折扣相同，可后续编辑
                "discount_3y": disc_rate,
                "price_45": int(yearly_price * 0.45),
                "price_55": int(yearly_price * 0.55),
                "discount_desc": extra_cell,
                "remark": remark_cell,
                "require_host": False,
                "host_id": None
            }

            if is_host:
                hosts.append(entry)
            else:
                products.append(entry)
        except (ValueError, IndexError):
            # 解析失败，跳过该行
            continue

    return products, hosts


def export_to_json(products, hosts):
    data = {"products": products, "hosts": hosts}
    save_path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')], title='导出为 JSON')
    if save_path:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        messagebox.showinfo('导出成功', f'已保存至 {save_path}')


# ------------------- UI 构建 -------------------
class PriceManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('天翼云报价维护系统')
        self.root.geometry('1200x720')
        self.products, self.hosts = load_data()
        self.create_widgets()

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True)

        # 产品页
        prod_frame = ttk.Frame(notebook)
        notebook.add(prod_frame, text='安全产品')
        self.prod_tree = self.build_tree(prod_frame, self.products)
        # 主机页
        host_frame = ttk.Frame(notebook)
        notebook.add(host_frame, text='云主机')
        self.host_tree = self.build_tree(host_frame, self.hosts)

        # 底部操作按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text='保存至代码', command=self.on_save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='从 Markdown 导入', command=self.on_import).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='导出为 JSON', command=self.on_export).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='退出', command=self.root.quit).pack(side='right', padx=5)

    def build_tree(self, parent, data):
        columns = ('id', 'category', 'name', 'monthly_price', 'yearly_price',
                       'yearly_discount', 'discount_rate', 'discount_2y', 'discount_3y', 'remark')
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        col_titles = {
            'id': 'ID', 'category': '分类', 'name': '规格', 'monthly_price': '月价',
            'yearly_price': '年价', 'yearly_discount': '年折扣', 'discount_rate': '折扣率',
            'discount_2y': '2年折扣', 'discount_3y': '3年折扣', 'remark': '备注'
        }
        for col in columns:
            tree.heading(col, text=col_titles.get(col, col))
            tree.column(col, width=100, anchor='center')
        tree.column('name', width=220)
        tree.column('remark', width=160)
        for item in data:
            values = (item.get('id'), item.get('category'), item.get('name'),
                      item.get('monthly_price'), item.get('yearly_price'),
                      item.get('yearly_discount'), item.get('discount_rate'),
                      item.get('discount_2y'), item.get('discount_3y'), item.get('remark'))
            tree.insert('', 'end', values=values)
        tree.pack(fill='both', expand=True)
        tree.bind('<Double-1>', self.on_edit)
        return tree

    def on_edit(self, event):
        tree = event.widget
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, 'values')
        edit_win = tk.Toplevel(self.root)
        edit_win.title('编辑记录')
        fields = ('id', 'category', 'name', 'monthly_price', 'yearly_price',
                       'yearly_discount', 'discount_rate', 'discount_2y', 'discount_3y', 'remark')
        entries = {}
        for i, field in enumerate(fields):
            tk.Label(edit_win, text=field).grid(row=i, column=0, sticky='e', padx=5, pady=2)
            var = tk.StringVar(value=str(values[i]) if values[i] is not None else '')
            ent = tk.Entry(edit_win, textvariable=var, width=55)
            ent.grid(row=i, column=1, padx=5, pady=2)
            entries[field] = var

        def save_changes():
            new_vals = {f: entries[f].get() for f in fields}
            target_list = self.products if tree == self.prod_tree else self.hosts
            for obj in target_list:
                if str(obj.get('id')) == new_vals['id']:
                    try:
                        obj['category'] = new_vals['category']
                        obj['name'] = new_vals['name']
                        obj['monthly_price'] = int(new_vals['monthly_price'])
                        obj['yearly_price'] = int(new_vals['yearly_price'])
                        obj['yearly_discount'] = float(new_vals['yearly_discount'])
                        obj['discount_rate'] = float(new_vals['discount_rate'])
                        obj['discount_2y'] = float(new_vals['discount_2y'])
                        obj['discount_3y'] = float(new_vals['discount_3y'])
                        obj['remark'] = new_vals['remark']
                    except ValueError:
                        messagebox.showerror('输入错误', '请检查数值字段格式是否正确')
                        return
                    break
            # 刷新树
            for i in tree.get_children():
                tree.delete(i)
            for obj in target_list:
                vals = (obj.get('id'), obj.get('category'), obj.get('name'),
                        obj.get('monthly_price'), obj.get('yearly_price'),
                        obj.get('yearly_discount'), obj.get('discount_rate'),
                        obj.get('discount_2y'), obj.get('discount_3y'), obj.get('remark'))
                tree.insert('', 'end', values=vals)
            edit_win.destroy()

        ttk.Button(edit_win, text='保存', command=save_changes).grid(
            row=len(fields), column=0, columnspan=2, pady=8)

    def on_save(self):
        save_to_quote_generator(self.products, self.hosts)

    def on_import(self):
        md_path = filedialog.askopenfilename(
            title='选择 Markdown 报价表',
            initialdir=os.path.join(BASE_DIR, 'knowledge-base', 'inbox'),
            filetypes=[('Markdown', '*.md'), ('所有文件', '*.*')]
        )
        if md_path:
            prods, hosts = import_from_markdown(md_path)
            if prods:
                self.products = prods
                for i in self.prod_tree.get_children():
                    self.prod_tree.delete(i)
                for obj in self.products:
                    vals = (obj.get('id'), obj.get('category'), obj.get('name'),
                            obj.get('monthly_price'), obj.get('yearly_price'),
                            obj.get('yearly_discount'), obj.get('discount_rate'), obj.get('remark'))
                    self.prod_tree.insert('', 'end', values=vals)
            if hosts:
                self.hosts = hosts
                for i in self.host_tree.get_children():
                    self.host_tree.delete(i)
                for obj in self.hosts:
                    vals = (obj.get('id'), obj.get('category'), obj.get('name'),
                            obj.get('monthly_price'), obj.get('yearly_price'),
                            obj.get('yearly_discount'), obj.get('discount_rate'), obj.get('remark'))
                    self.host_tree.insert('', 'end', values=vals)
            imported_msg = f'已导入 {len(prods)} 个产品、{len(hosts)} 个云主机'
            messagebox.showinfo('导入完成', imported_msg)

    def on_export(self):
        export_to_json(self.products, self.hosts)


if __name__ == '__main__':
    root = tk.Tk()
    app = PriceManagerApp(root)
    root.mainloop()