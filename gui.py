# -*- coding: utf-8 -*-
"""
天翼云等保专区报价工具 - GUI 交互界面
功能：
- 左侧树形列表展示所有安全产品，双击可添加到右侧已选列表。
- 右侧列表显示已选产品，支持修改数量或移除。
- 实时汇总展示月/年/折扣价等信息。
- 点击 "生成报价" 将生成 Excel 报价表并保存到 quote/ 目录。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# 确保可以导入项目内部模块
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from scripts.quote_generator import (
    get_all_products,
    get_all_hosts,
    get_product_by_id,
    get_host_by_id,
    calculate_price,
    generate_quote_data,
    get_totals,
)
from scripts.main import create_quote_excel

# ---------- GUI 构建 ----------
class QuoteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("天翼云等保专区报价工具（V20）")
        self.root.geometry("1000x680")
        self.selected_products = []  # List[Dict]
        self.quantities = {}        # product_id -> int
        self.years_var = tk.StringVar(value="1")

        self.build_ui()
        self.refresh_summary()

    # ---- UI ----
    def build_ui(self):
        # 设置整体风格
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', font=('微软雅黑', 10))
        style.configure('Treeview.Heading', font=('微软雅黑', 11, 'bold'))
        style.configure('TLabel', font=('微软雅黑', 10))
        style.configure('TButton', font=('微软雅黑', 10))

        # 主容器分为左右两侧
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ====== 左侧：产品树 ======
        left_frame = ttk.Frame(paned, width=300)
        paned.add(left_frame, weight=1)
        tree_container = ttk.Frame(left_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.product_tree = ttk.Treeview(tree_container, show='tree')
        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.product_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.product_tree.configure(yscrollcommand=tree_scroll.set)
        self.product_tree.bind('<Double-1>', self.on_product_double_click)
        self.populate_product_tree()

        # ====== 右侧：已选列表 + 汇总 + 按钮 ======
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        # 已选产品列表
        prod_label = ttk.Label(right_frame, text="已选产品（双击左侧添加）")
        prod_label.pack(anchor='w', padx=5, pady=2)
        self.selected_listbox = tk.Listbox(right_frame, height=12, font=('微软雅黑', 10))
        self.selected_listbox.pack(fill=tk.X, padx=5)
        self.selected_listbox.bind('<Double-Button-1>', self.on_selected_double_click)

        # 汇总文本框
        summary_label = ttk.Label(right_frame, text="费用汇总")
        summary_label.pack(anchor='w', padx=5)
        self.summary_text = tk.Text(right_frame, height=6, state='disabled', font=('微软雅黑', 10))
        self.summary_text.pack(fill=tk.X, padx=5, pady=2)

        # 报价年数选择 + 操作按钮
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        years_row = ttk.Frame(bottom_frame)
        years_row.pack(fill=tk.X, pady=2)
        ttk.Label(years_row, text="报价年数:").pack(side=tk.LEFT)
        ttk.Combobox(years_row, textvariable=self.years_var, values=["1", "2", "3"], width=5, state='readonly').pack(side=tk.LEFT, padx=5)
        self.years_var.trace_add('write', lambda *_: self.refresh_summary())

        btn_row = ttk.Frame(bottom_frame)
        btn_row.pack(fill=tk.X, pady=2)
        ttk.Button(btn_row, text="生成报价", command=self.generate_quote).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="清空全部", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    # ---- 产品树 ----
    def _match_host_for_product(self, prod_name, hosts_list):
        """为产品查找对应的云主机（支持模糊匹配）"""
        # 策略1：精确匹配 产品名+"-云主机"
        exact = prod_name + "-云主机"
        for h in hosts_list:
            if h['name'] == exact:
                return h
        # 策略2：去掉产品名末尾的变体后缀再匹配
        # 如 "Web应用防火墙-独享版-单机版" -> 去掉"-单机版" -> "Web应用防火墙-独享版-云主机"
        suffixes_to_strip = ['-单机版', '-域名扩展包', '-带宽扩展包', '-业务扩展包', '-规则扩展包']
        for suffix in suffixes_to_strip:
            if prod_name.endswith(suffix):
                base = prod_name[:-len(suffix)]
                expected = base + "-云主机"
                for h in hosts_list:
                    if h['name'] == expected:
                        return h
        # 策略3：按前缀匹配（取产品名第一段+'-'+第二段作为前缀）
        parts = prod_name.split('-')
        if len(parts) >= 2:
            prefix = parts[0] + '-' + parts[1]
            matches = [h for h in hosts_list if h['name'].startswith(prefix + '-') and h['name'].endswith('-云主机')]
            if len(matches) == 1:
                return matches[0]
        return None

    def populate_product_tree(self):
        products = get_all_products()
        hosts_list = get_all_hosts()
        used_host_ids = set()  # 跟踪已分配的云主机ID，防止重复insert
        categories = {}
        for p in products:
            cat = p['category']
            categories.setdefault(cat, []).append(p)
        for cat, items in categories.items():
            cat_id = self.product_tree.insert('', 'end', text=cat, open=True)
            for prod in items:
                prod_iid = f"p{prod['id']}"
                self.product_tree.insert(cat_id, 'end', iid=prod_iid, text=prod['name'])
                # 查找对应的云主机（支持多种匹配策略），跳过已使用的
                host = self._match_host_for_product(prod['name'], hosts_list)
                if host and host['id'] not in used_host_ids:
                    used_host_ids.add(host['id'])
                    host_iid = f"h{host['id']}"
                    self.product_tree.insert(prod_iid, 'end', iid=host_iid, text=f"[云主机] {host['name']}")
        # 在最底部添加管理节点-云主机（独立根级项目）
        if 69 not in used_host_ids:
            mgmt_host = get_host_by_id(69)
            if mgmt_host:
                self.product_tree.insert('', 'end', iid="h69", text=f"[管理节点] {mgmt_host['name']}")

    def on_product_double_click(self, event):
        """双击产品树：将产品或云主机添加到已选列表"""
        # 方式1：用 identify 直接定位点击位置
        item = self.product_tree.identify('row', event.x, event.y)
        # 方式2：如果 identify 失败，回退到 focus
        if not item:
            item = self.product_tree.focus()
        if not item:
            return
        if item.startswith('p'):
            prod_id = int(item[1:])
            prod = get_product_by_id(prod_id)
            if not prod:
                return
            # 只和已有产品比，不和云主机混在一起（避免ID冲突）
            existing_prod_ids = {p['id'] for p in self.selected_products if '云主机' not in p.get('category', '')}
            if prod_id not in existing_prod_ids:
                self.selected_products.append(prod)
                self.quantities[prod_id] = 1
                self.refresh_selected_list()
                self.refresh_summary()
        elif item.startswith('h'):
            host_id = int(item[1:])
            host = get_host_by_id(host_id)
            if not host:
                return
            # 只和已有云主机比，不和产品混在一起（避免ID冲突）
            existing_host_ids = {p['id'] for p in self.selected_products if '云主机' in p.get('category', '')}
            if host_id not in existing_host_ids:
                self.selected_products.append(host)
                self.quantities[host_id] = 1
                self.refresh_selected_list()
                self.refresh_summary()

    # ---- 已选列表 ----
    def refresh_selected_list(self):
        self.selected_listbox.delete(0, tk.END)
        for item in self.selected_products:
            pid = item['id']
            qty = self.quantities.get(pid, 1)
            if '云主机' in item.get('category', ''):
                display = f"[云主机] {item['name']}  × {qty}"
            else:
                display = f"[{pid}] {item['name']}  × {qty}"
            self.selected_listbox.insert(tk.END, display)

    def on_selected_double_click(self, event):
        """双击已选列表：安全产品和云主机都可修改数量或删除"""
        sel = self.selected_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.selected_products[idx]
        pid = item['id']
        is_host = '云主机' in item.get('category', '')
        prompt_text = f"{item['name']} 的{'云主机' if is_host else ''}数量:"
        qty_str = simpledialog.askstring("修改数量", prompt_text, initialvalue=str(self.quantities.get(pid, 1)))
        if qty_str is None:
            return
        if qty_str.strip() == "":
            if messagebox.askyesno("删除确认", f"确定移除 {item['name']} 吗？"):
                del self.selected_products[idx]
                self.quantities.pop(pid, None)
                self.refresh_selected_list()
                self.refresh_summary()
            return
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "数量必须为正整数")
            return
        self.quantities[pid] = qty
        self.refresh_selected_list()
        self.refresh_summary()

    # ---- 汇总 ----
    def refresh_summary(self):
        try:
            years = int(self.years_var.get())
        except ValueError:
            years = 1
        quote_items = []
        for prod in self.selected_products:
            pid = prod['id']
            qty = self.quantities.get(pid, 1)
            prices = calculate_price(prod, qty)
            quote_items.append({
                "seq": pid,
                "product": prod["name"],
                "spec": prod["spec"],
                "qty": qty,
                "monthly": prices["monthly"],
                "yearly": prices["yearly"],
                "discounted": prices["discounted"],
                "price_45": prices["price_45"],
                "price_55": prices["price_55"],
                "discount_desc": prod.get("discount_desc", ""),
                "remark": prod.get("remark", ""),
                "category": prod.get("category", ""),
                "is_host": ("云主机" in prod.get("category", "")),
            })
        totals = get_totals(quote_items)
        monthly = totals['monthly']
        yearly = totals['yearly']
        discounted = totals['discounted']
        total_yearly = yearly * years
        total_discounted = discounted * years
        total_45 = totals['price_45'] * years
        total_55 = totals['price_55'] * years
        self.summary_text.configure(state='normal')
        self.summary_text.delete('1.0', tk.END)
        self.summary_text.insert(tk.END, f"产品数量: {len(quote_items)}\n")
        self.summary_text.insert(tk.END, f"标准价 (1月): ¥{monthly:.2f}\n")
        self.summary_text.insert(tk.END, f"标准价 ({years}年): ¥{total_yearly:.2f}\n")
        self.summary_text.insert(tk.END, f"折扣价 ({years}年): ¥{total_discounted:.2f}\n")
        self.summary_text.insert(tk.END, f"4.5折结算价: ¥{total_45:.2f}\n")
        self.summary_text.insert(tk.END, f"5.5折结算价: ¥{total_55:.2f}\n")
        self.summary_text.configure(state='disabled')

    # ---- 删除选中 ----
    def delete_selected(self):
        sel = self.selected_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先在已选列表中选择要删除的项目。")
            return
        idx = sel[0]
        item = self.selected_products[idx]
        if messagebox.askyesno("删除确认", f"确定移除 {item['name']} 吗？"):
            self.quantities.pop(item['id'], None)
            del self.selected_products[idx]
            self.refresh_selected_list()
            self.refresh_summary()

    # ---- 生成报价 ----
    def generate_quote(self):
        if not self.selected_products:
            messagebox.showwarning("未选择产品", "请先在左侧选择至少一个安全产品。")
            return
        try:
            years = int(self.years_var.get())
        except ValueError:
            years = 1
        data = generate_quote_data(
            list(self.selected_products), self.quantities,
            include_host=False, include_mgmt_host=False
        )
        totals = get_totals(data)
        quote_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'quote')
        os.makedirs(quote_dir, exist_ok=True)
        default_name = f"天翼云等保专区安全产品报价表_自定义_{self._timestamp()}.xlsx"
        out_path = filedialog.asksaveasfilename(
            initialdir=quote_dir, title="保存报价表",
            defaultextension=".xlsx", filetypes=[('Excel 文件', '*.xlsx')],
            initialfile=default_name
        )
        if not out_path:
            return
        create_quote_excel(data, totals, out_path, "天翼云等保专区安全产品报价表（自定义）", years=years)
        messagebox.showinfo("生成成功", f"报价表已保存至:\n{out_path}")
        try:
            os.startfile(os.path.dirname(out_path))
        except Exception:
            pass

    def _timestamp(self):
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    # ---- 清空 ----
    def clear_all(self):
        if messagebox.askyesno("确认", "确定清空已选产品吗？"):
            self.selected_products.clear()
            self.quantities.clear()
            self.refresh_selected_list()
            self.refresh_summary()

# ---------- 主入口 ----------
if __name__ == '__main__':
    root = tk.Tk()
    app = QuoteApp(root)
    root.mainloop()
