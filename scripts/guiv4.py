# -*- coding: utf-8 -*-
"""
天翼云等保专区报价工具 - GUI 交互界面（版本4）
功能：
- 左侧树形列表展示所有安全产品，云主机作为对应安全产品的子目录显示，双击即可加入右侧已选列表。
- 右侧仅保留已选产品列表、费用汇总、生成报价、清空全部按钮。
- 界面添加背景图片（蓝色渐变），提升视觉效果。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# 确保可以导入项目内部模块
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from scripts.quote_generator import (
    get_all_products,
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
        self.root.title("天翼云等保专区报价工具（V4）")
        self.root.geometry("1000x680")
        self.selected_products = []  # List[Dict]
        self.quantities = {}        # product_id -> int

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

        # 背景图片
        bg_path = os.path.join(base_dir, 'scripts', '蓝色渐变背景_适用于_1000x680_窗口的_GUI_简约_2026-04-26T16-00-56.png')
        self.bg_image = tk.PhotoImage(file=bg_path)
        bg_label = tk.Label(self.root, image=self.bg_image)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # 主容器分为左右两侧
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 左侧：产品树（带滚动条）
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

        # 右侧：已选列表、费用汇总、操作按钮（不再有云主机复选框）
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        # 已选产品列表
        prod_label = ttk.Label(right_frame, text="已选产品（双击左侧添加）")
        prod_label.pack(anchor='w', padx=5, pady=2)
        self.selected_listbox = tk.Listbox(right_frame, height=10, font=('微软雅黑', 10))
        self.selected_listbox.pack(fill=tk.X, padx=5)
        self.selected_listbox.bind('<Double-Button-1>', self.on_selected_double_click)

        # 费用汇总文本框（只读）
        summary_label = ttk.Label(right_frame, text="费用汇总")
        summary_label.pack(anchor='w', padx=5)
        self.summary_text = tk.Text(right_frame, height=6, state='disabled', font=('微软雅黑', 10))
        self.summary_text.pack(fill=tk.X, padx=5, pady=2)

        # 操作按钮（居中）
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="生成报价", command=self.generate_quote).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空全部", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        # 确保背景在最底层
        bg_label.lower()

    # ---- 产品树 ----
    def populate_product_tree(self):
        products = get_all_products()
        categories = {}
        for p in products:
            cat = p['category']
            categories.setdefault(cat, []).append(p)
        for cat, items in categories.items():
            cat_id = self.product_tree.insert('', 'end', text=cat, open=True)
            for prod in items:
                prod_iid = f"p{prod['id']}"
                self.product_tree.insert(cat_id, 'end', iid=prod_iid, text=prod['name'])
                if prod.get('require_host') and prod.get('host_id'):
                    host = get_host_by_id(prod['host_id'])
                    if host:
                        host_iid = f"h{host['id']}"
                        self.product_tree.insert(prod_iid, 'end', iid=host_iid, text=f"[云主机] {host['name']}")

    def on_product_double_click(self, event):
        item = self.product_tree.focus()
        if not item:
            return
        if item.startswith('p'):
            prod_id = int(item[1:])
            prod = get_product_by_id(prod_id)
            if not prod:
                return
            if prod_id not in [p['id'] for p in self.selected_products]:
                self.selected_products.append(prod)
                self.quantities[prod_id] = 1
                self.refresh_selected_list()
                self.refresh_summary()
        elif item.startswith('h'):
            host_id = int(item[1:])
            host = get_host_by_id(host_id)
            if not host:
                return
            if host_id not in [p['id'] for p in self.selected_products]:
                self.selected_products.append(host)
                self.refresh_selected_list()
                self.refresh_summary()

    # ---- 已选列表 ----
    def refresh_selected_list(self):
        self.selected_listbox.delete(0, tk.END)
        for item in self.selected_products:
            if item.get('category') == '云主机':
                display = f"[云主机] {item['name']}"
            else:
                pid = item['id']
                qty = self.quantities.get(pid, 1)
                display = f"[{pid}] {item['name']}  × {qty}"
            self.selected_listbox.insert(tk.END, display)

    def on_selected_double_click(self, event):
        sel = self.selected_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.selected_products[idx]
        if item.get('category') == '云主机':
            if messagebox.askyesno("删除确认", f"确定从已选列表中移除云主机 {item['name']} 吗？"):
                del self.selected_products[idx]
                self.refresh_selected_list()
                self.refresh_summary()
            return
        pid = item['id']
        qty_str = tk.simpledialog.askstring("修改数量", f"{item['name']} 的数量:", initialvalue=str(self.quantities.get(pid, 1)))
        if qty_str is None:
            return
        if qty_str.strip() == "":
            del self.selected_products[idx]
            self.quantities.pop(pid, None)
        else:
            if qty_str.isdigit() and int(qty_str) > 0:
                self.quantities[pid] = int(qty_str)
            else:
                messagebox.showwarning("无效输入", "数量必须为正整数")
        self.refresh_selected_list()
        self.refresh_summary()

    # ---- 汇总 ----
    def refresh_summary(self):
        data = []
        for prod in self.selected_products:
            pid = prod['id']
            qty = self.quantities.get(pid, 1)
            data.append((prod, qty))
        quote_items = []
        for prod, qty in data:
            prices = calculate_price(prod, qty)
            quote_items.append({
                "seq": 0,
                "product": prod["name"],
                "spec": prod["spec"],
                "qty": qty,
                "monthly": prices["monthly"],
                "yearly": prices["yearly"],
                "discounted": prices["discounted"],
                "price_45": prices["price_45"],
                "price_55": prices["price_55"],
                "discount_desc": prod["discount_desc"],
                "remark": prod["remark"],
                "category": prod["category"],
                "is_host": False,
            })
        totals = get_totals(quote_items)
        self.summary_text.configure(state='normal')
        self.summary_text.delete('1.0', tk.END)
        self.summary_text.insert(tk.END, f"产品数量: {len(quote_items)}\n")
        self.summary_text.insert(tk.END, f"标准价 (1月): ¥{totals['monthly']:.2f}\n")
        self.summary_text.insert(tk.END, f"标准价 (1年): ¥{totals['yearly']:.2f}\n")
        self.summary_text.insert(tk.END, f"折扣价 (1年): ¥{totals['discounted']:.2f}\n")
        self.summary_text.insert(tk.END, f"4.5折结算价: ¥{totals['price_45']:.2f}\n")
        self.summary_text.insert(tk.END, f"5.5折结算价: ¥{totals['price_55']:.2f}\n")
        self.summary_text.configure(state='disabled')

    # ---- 生成报价 ----
    def generate_quote(self):
        if not self.selected_products:
            messagebox.showwarning("未选择产品", "请先在左侧选择至少一个安全产品或云主机。")
            return
        data = generate_quote_data(self.selected_products, self.quantities, include_hosts=False, include_mgmt_host=False)
        totals = get_totals(data)
        quote_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'quote')
        os.makedirs(quote_dir, exist_ok=True)
        default_name = f"天翼云等保专区安全产品报价表_自定义_{self._timestamp()}.xlsx"
        out_path = filedialog.asksaveasfilename(initialdir=quote_dir, title="保存报价表", defaultextension=".xlsx", filetypes=[('Excel 文件', '*.xlsx')], initialfile=default_name)
        if not out_path:
            return
        create_quote_excel(data, totals, out_path, "天翼云等保专区安全产品报价表（自定义）")
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
