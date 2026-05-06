# -*- coding: utf-8 -*-
"""
天翼云等保专区报价工具 - GUI 交互界面（版本8）
功能升级：
- 新增报价年份选项（1年、2年、3年）
- 根据选择的年份动态计算标准价、折扣价、4.5折、5.5折
- 界面保持 V5 的渐变背景和布局，仅在右侧汇总区加入年份选择控件
- 修复导入错误，使用 get_all_hosts 替代缺失的 get_host_by_id
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# 确保可以导入项目内部模块
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的临时目录
    base_dir = os.path.abspath(os.path.join(sys._MEIPASS, '..'))
else:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from quote_generator import (
    get_all_products,
    get_product_by_id,
    get_all_hosts,
    calculate_price,
    generate_quote_data,
    get_totals,
)
from main import create_quote_excel

# 辅助函数：根据 host_id 获取云主机信息
def get_host_by_id(host_id: int):
    for h in get_all_hosts():
        if h.get('id') == host_id:
            return h
    return None

# ---------- GUI 构建 ----------
class QuoteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("天翼云等保专区报价工具（V8）")
        self.root.geometry("1000x720")
        self.selected_products = []  # List[Dict]
        self.quantities = {}        # product_id -> int
        self.year_var = tk.IntVar(value=1)  # 报价年数，默认 1 年

        self.build_ui()
        self.refresh_summary()

    # ---- UI ----
    def build_ui(self):
        # 设置窗口背景颜色（蓝色渐变效果通过Canvas实现）
        self.root.configure(bg='#1a5276')
        
        # 创建Canvas作为背景
        self.canvas = tk.Canvas(self.root, bg='#1a5276', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绘制渐变背景
        self.draw_gradient_background()
        
        # 设置整体风格
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', font=('微软雅黑', 10))
        style.configure('Treeview.Heading', font=('微软雅黑', 11, 'bold'))
        style.configure('TLabel', font=('微软雅黑', 10))
        style.configure('TButton', font=('微软雅黑', 10))
        style.configure('TCombobox', font=('微软雅黑', 10))

        # 主容器分为左右两侧（放在Canvas上）
        paned = ttk.Panedwindow(self.canvas, orient=tk.HORIZONTAL)
        self.canvas.create_window(500, 360, window=paned, width=980, height=680)

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

        # 右侧：已选列表、费用汇总、操作按钮、年份选择
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
        self.summary_text = tk.Text(right_frame, height=8, state='disabled', font=('微软雅黑', 10))
        self.summary_text.pack(fill=tk.X, padx=5, pady=2)

        # 年份选择控件
        year_frame = ttk.Frame(right_frame)
        year_frame.pack(fill=tk.X, pady=4)
        ttk.Label(year_frame, text="报价年数：").pack(side=tk.LEFT, padx=2)
        year_combo = ttk.Combobox(year_frame, textvariable=self.year_var, values=[1,2,3], width=5, state='readonly')
        year_combo.pack(side=tk.LEFT)
        year_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_summary())

        # 操作按钮（居中）
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="生成报价", command=self.generate_quote).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空全部", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def draw_gradient_background(self):
        """绘制渐变背景"""
        colors = self.generate_gradient_colors('#1a5276', '#5dade2', 100)
        height = 720
        width = 1000
        for i, color in enumerate(colors):
            y1 = int(height * i / len(colors))
            y2 = int(height * (i + 1) / len(colors))
            self.canvas.create_rectangle(0, y1, width, y2, fill=color, outline=color)

    def generate_gradient_colors(self, start_color, end_color, steps):
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(*rgb)
        start_rgb = hex_to_rgb(start_color)
        end_rgb = hex_to_rgb(end_color)
        colors = []
        for i in range(steps):
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * i / (steps - 1))
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * i / (steps - 1))
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * i / (steps - 1))
            colors.append(rgb_to_hex((r, g, b)))
        return colors

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
                if not self.product_tree.exists(prod_iid):
                    self.product_tree.insert(cat_id, 'end', iid=prod_iid, text=prod['name'])
                if prod.get('require_host') and prod.get('host_id'):
                    host = get_host_by_id(prod['host_id'])
                    if host:
                        host_iid = f"h{host['id']}"
                        if not self.product_tree.exists(host_iid):
                            self.product_tree.insert(prod_iid, 'end', iid=host_iid, text=f"[云主机] {host['name']}")
        # 添加独立的云主机节点
        hosts_root = self.product_tree.insert('', 'end', iid='hosts_root', text='云主机', open=True)
        for host in get_all_hosts():
            host_iid = f"h{host['id']}"
            if not self.product_tree.exists(host_iid):
                self.product_tree.insert(hosts_root, 'end', iid=host_iid, text=f"[云主机] {host['name']}")


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
        qty_str = simpledialog.askstring("修改数量", f"{item['name']} 的数量:", initialvalue=str(self.quantities.get(pid, 1)))
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
    def _calc_price_for_years(self, product, qty, years):
        """返回包含月、年、折扣、4.5折、5.5折的价格字典（按 years 年累计）"""
        monthly = product.get('monthly_price', 0) * qty
        yearly_one = product.get('yearly_price', 0) * qty
        yearly_total = yearly_one * years
        discounted_one = yearly_one * product.get('yearly_discount', 1)
        discounted_total = discounted_one * years
        price_45 = discounted_total * 0.45
        price_55 = discounted_total * 0.55
        return {
            'monthly': monthly,
            'yearly': yearly_total,
            'discounted': discounted_total,
            'price_45': price_45,
            'price_55': price_55,
        }

    def refresh_summary(self):
        years = self.year_var.get()
        quote_items = []
        for prod in self.selected_products:
            pid = prod['id']
            qty = self.quantities.get(pid, 1)
            prices = self._calc_price_for_years(prod, qty, years)
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
        self.summary_text.insert(tk.END, f"标准价 (月): ¥{totals['monthly']:.2f}\n")
        self.summary_text.insert(tk.END, f"标准价 ({years}年): ¥{totals['yearly']:.2f}\n")
        self.summary_text.insert(tk.END, f"折扣价 ({years}年): ¥{totals['discounted']:.2f}\n")
        self.summary_text.insert(tk.END, f"4.5折结算价 ({years}年): ¥{totals['price_45']:.2f}\n")
        self.summary_text.insert(tk.END, f"5.5折结算价 ({years}年): ¥{totals['price_55']:.2f}\n")
        self.summary_text.configure(state='disabled')

    # ---- 生成报价 ----
    def generate_quote(self):
        if not self.selected_products:
            messagebox.showwarning("未选择产品", "请先在左侧选择至少一个安全产品或云主机。")
            return
        years = self.year_var.get()
        data = generate_quote_data(self.selected_products, self.quantities, include_host=False, include_mgmt_host=False)
        for row in data:
            row['yearly'] = row['yearly'] * years
            row['discounted'] = row['discounted'] * years
            row['price_45'] = row['price_45'] * years
            row['price_55'] = row['price_55'] * years
        totals = get_totals(data)
        quote_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'quote')
        os.makedirs(quote_dir, exist_ok=True)
        default_name = f"天翼云等保专区安全产品报价表_自定义_{self._timestamp()}_{years}年.xlsx"
        out_path = filedialog.asksaveasfilename(initialdir=quote_dir, title="保存报价表", defaultextension=".xlsx", filetypes=[('Excel 文件', '*.xlsx')], initialfile=default_name)
        if not out_path:
            return
        create_quote_excel(data, totals, out_path, f"天翼云等保专区安全产品报价表（自定义，{years}年）")
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
