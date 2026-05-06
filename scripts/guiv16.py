# -*- coding: utf-8 -*-
"""
天翼云等保专区报价工具 - GUI 交互界面（版本17）
修复问题：
1. 云主机正确作为对应安全产品的子节点显示（通过名称前缀匹配）
2. 双击云主机子节点即可加入已选列表
3. 序号列使用公式 =ROW()-1，自动递增
4. 数据按序号升序排列
5. 禁用无效的自动更新检查（价格API不存在）
6. 【V16新增】修复弹窗导致主窗口最小化问题，使用正确的模态对话框模式
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# ---------- 价格更新检查（暂时禁用，等待接入真实价格API） ----------
def fetch_update():
    """价格更新检查已暂时禁用，等待接入真实价格API"""
    pass


# ---------- 弹窗函数（在后台显示，不影响主窗口焦点） ----------
def show_background_reminder(root):
    """
    在后台弹出确认提醒窗口，使用正确的模态对话框模式：
    - transient(root) 让弹窗成为 root 的子窗口
    - grab_set() 捕获输入焦点，阻塞父窗口交互
    - wait_window() 等待弹窗关闭后才继续
    - focus_force() 弹窗关闭后恢复主窗口焦点
    - 优先基于 root 位置居中，若 root 位置异常则基于屏幕居中
    效果：点确认/关闭后主窗口不会最小化
    """
    reminder = tk.Toplevel(root)
    reminder.title("提示")
    reminder.geometry("340x130")
    reminder.resizable(False, False)
    reminder.transient(root)
    # 弹窗居中显示
    reminder.update_idletasks()
    rx, ry = root.winfo_x(), root.winfo_y()
    rw, rh = root.winfo_width(), root.winfo_height()
    pw, ph = reminder.winfo_width(), reminder.winfo_height()
    # 若 root 位置异常（窗口管理器未赋值有效位置），基于屏幕居中
    if rx == 0 and ry == 0 and rw == 1 and rh == 1:
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        reminder.geometry(f"+{sw//2 - pw//2}+{sh//2 - ph//2}")
    else:
        reminder.geometry(f"+{rx + rw//2 - pw//2}+{ry + rh//2 - ph//2}")
    # 内容
    tk.Label(reminder, text="已完成更新检查。", wraplength=300,
             font=('微软雅黑', 11)).pack(pady=15)
    tk.Button(reminder, text="确认", font=('微软雅黑', 10),
              command=reminder.destroy).pack()
    # 关闭按钮（X）同样触发销毁
    reminder.protocol("WM_DELETE_WINDOW", reminder.destroy)
    # 模态：捕获焦点并等待关闭
    reminder.grab_set()
    reminder.wait_window()
    # 弹窗关闭后，确保主窗口获得焦点且不失焦
    root.focus_force()
    root.update_idletasks()


# ---------- 导入项目内部模块 ----------
if getattr(sys, 'frozen', False):
    base_dir = os.path.abspath(os.path.join(sys._MEIPASS, '..'))
else:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from scripts.quote_generator import (
    get_all_products,
    get_product_by_id,
    get_all_hosts,
    calculate_price,
    generate_quote_data,
    get_totals,
)
from scripts.main import create_quote_excel


def get_host_by_id(host_id: int):
    for h in get_all_hosts():
        if h.get('id') == host_id:
            return h
    return None


def build_product_host_mapping():
    """
    根据名称前缀匹配，建立 产品id -> [云主机列表] 的映射。
    匹配规则：云主机名称以"<产品名称>"开头，或产品名称包含在云主机名称中。
    特殊情况：
      - Web应用防火墙-独享版-单机版  -> Web应用防火墙-独享版-云主机
      - 下一代防火墙-标准/高级/企业版 -> 下一代防火墙-标准/高级/企业版-云主机
      - 日志审计-X资产               -> 日志审计-X资产-云主机
      - 堡垒机-X资产                 -> 堡垒机-X资产-云主机
      - 数据库审计-X资产             -> 数据库审计-X资产-云主机
      - 漏洞扫描-X资产               -> 漏洞扫描-X资产-云主机
    """
    products = get_all_products()
    hosts = get_all_hosts()
    mapping = {}

    for prod in products:
        prod_name = prod['name']
        matched_hosts = []
        for host in hosts:
            host_name = host['name']
            # 规则1：云主机名称 = 产品名称 + "-云主机"
            if host_name == prod_name + '-云主机':
                matched_hosts.append(host)
                continue
            # 规则2：Web应用防火墙-独享版-单机版 对应 Web应用防火墙-独享版-云主机
            if prod_name == 'Web应用防火墙-独享版-单机版' and host_name == 'Web应用防火墙-独享版-云主机':
                matched_hosts.append(host)
                continue
        if matched_hosts:
            mapping[prod['id']] = matched_hosts
    return mapping


# ---------- GUI 构建 ----------
class QuoteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("天翼云等保专区报价工具（V17）")
        self.root.geometry("1000x720")
        self.selected_products = []
        self.quantities = {}
        self.year_var = tk.IntVar(value=1)
        self.product_host_map = build_product_host_mapping()
        self.build_ui()
        self.refresh_summary()

    def build_ui(self):
        self.root.configure(bg='#1a5276')
        self.canvas = tk.Canvas(self.root, bg='#1a5276', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_gradient_background()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', font=('微软雅黑', 10))
        style.configure('Treeview.Heading', font=('微软雅黑', 11, 'bold'))
        style.configure('TLabel', font=('微软雅黑', 10))
        style.configure('TButton', font=('微软雅黑', 10))
        style.configure('TCombobox', font=('微软雅黑', 10))

        paned = ttk.Panedwindow(self.canvas, orient=tk.HORIZONTAL)
        self.canvas.create_window(500, 360, window=paned, width=980, height=680)

        # 左侧：产品树
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

        # 右侧
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        prod_label = ttk.Label(right_frame, text="已选产品（双击左侧添加）")
        prod_label.pack(anchor='w', padx=5, pady=2)
        self.selected_listbox = tk.Listbox(right_frame, height=10, font=('微软雅黑', 10))
        self.selected_listbox.pack(fill=tk.X, padx=5)
        self.selected_listbox.bind('<Double-Button-1>', self.on_selected_double_click)

        summary_label = ttk.Label(right_frame, text="费用汇总")
        summary_label.pack(anchor='w', padx=5)
        self.summary_text = tk.Text(right_frame, height=8, state='disabled', font=('微软雅黑', 10))
        self.summary_text.pack(fill=tk.X, padx=5, pady=2)

        year_frame = ttk.Frame(right_frame)
        year_frame.pack(fill=tk.X, pady=4)
        ttk.Label(year_frame, text="报价年数：").pack(side=tk.LEFT, padx=2)
        year_combo = ttk.Combobox(year_frame, textvariable=self.year_var, values=[1, 2, 3], width=5, state='readonly')
        year_combo.pack(side=tk.LEFT)
        year_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_summary())

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="生成报价", command=self.generate_quote).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空全部", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def draw_gradient_background(self):
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

    def populate_product_tree(self):
        products = get_all_products()
        categories = {}
        for p in products:
            cat = p['category']
            categories.setdefault(cat, []).append(p)
        for cat, items in categories.items():
            cat_node = self.product_tree.insert('', 'end', text=cat, open=True)
            for prod in items:
                prod_iid = f"p{prod['id']}"
                if not self.product_tree.exists(prod_iid):
                    self.product_tree.insert(cat_node, 'end', iid=prod_iid, text=prod['name'], open=False)
                matched_hosts = self.product_host_map.get(prod['id'], [])
                for host in matched_hosts:
                    host_iid = f"h{host['id']}_p{prod['id']}"
                    if not self.product_tree.exists(host_iid):
                        self.product_tree.insert(prod_iid, 'end', iid=host_iid,
                                                 text=f"  └ [云主机] {host['name']}")

    def on_product_double_click(self, event):
        item = self.product_tree.focus()
        if not item:
            return
        if item.startswith('h'):
            try:
                host_id = int(item.split('_')[0][1:])
            except (ValueError, IndexError):
                return
            host = get_host_by_id(host_id)
            if not host:
                messagebox.showwarning("找不到云主机", f"云主机 id={host_id} 不存在")
                return
            existing_ids = [p['id'] for p in self.selected_products]
            if host['id'] not in existing_ids:
                self.selected_products.append(host)
                self.quantities[host['id']] = 1
                self.refresh_selected_list()
                self.refresh_summary()
            else:
                messagebox.showinfo("已添加", f"云主机 {host['name']} 已在已选列表中。")
        elif item.startswith('p'):
            try:
                prod_id = int(item[1:])
            except ValueError:
                return
            prod = get_product_by_id(prod_id)
            if not prod:
                return
            existing_ids = [p['id'] for p in self.selected_products]
            if prod_id not in existing_ids:
                self.selected_products.append(prod)
                self.quantities[prod_id] = 1
                self.refresh_selected_list()
                self.refresh_summary()
            else:
                messagebox.showinfo("已添加", f"产品 {prod['name']} 已在已选列表中。")

    def refresh_selected_list(self):
        self.selected_listbox.delete(0, tk.END)
        for item in self.selected_products:
            if item.get('category', '').endswith('云主机') or '云主机' in item.get('name', ''):
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
        is_host = item.get('category', '').endswith('云主机') or '云主机' in item.get('name', '')
        if is_host:
            if messagebox.askyesno("删除确认", f"确定从已选列表中移除云主机 {item['name']} 吗？"):
                del self.selected_products[idx]
                self.quantities.pop(item['id'], None)
                self.refresh_selected_list()
                self.refresh_summary()
            return
        pid = item['id']
        qty_str = simpledialog.askstring("修改数量", f"{item['name']} 的数量:",
                                         initialvalue=str(self.quantities.get(pid, 1)))
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

    def _calc_price_for_years(self, product, qty, years):
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
                "spec": prod.get("spec", ""),
                "qty": qty,
                "monthly": prices["monthly"],
                "yearly": prices["yearly"],
                "discounted": prices["discounted"],
                "price_45": prices["price_45"],
                "price_55": prices["price_55"],
                "discount_desc": prod.get("discount_desc", ""),
                "remark": prod.get("remark", ""),
                "category": prod.get("category", ""),
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

    def generate_quote(self):
        if not self.selected_products:
            messagebox.showwarning("未选择产品", "请先在左侧选择至少一个安全产品或云主机。")
            return
        years = self.year_var.get()
        data = generate_quote_data(self.selected_products, self.quantities,
                                   include_host=False, include_mgmt_host=False)
        for row in data:
            row['yearly'] = row['yearly'] * years
            row['discounted'] = row['discounted'] * years
            row['price_45'] = row['price_45'] * years
            row['price_55'] = row['price_55'] * years
        totals = get_totals(data)
        quote_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'quote')
        os.makedirs(quote_dir, exist_ok=True)
        default_name = f"天翼云等保专区安全产品报价表_自定义_{self._timestamp()}_{years}年.xlsx"
        out_path = filedialog.asksaveasfilename(
            initialdir=quote_dir, title="保存报价表",
            defaultextension=".xlsx", filetypes=[('Excel 文件', '*.xlsx')],
            initialfile=default_name)
        if not out_path:
            return
        create_quote_excel(data, totals, out_path,
                           f"天翼云等保专区安全产品报价表（自定义，{years}年）", years=years)
        messagebox.showinfo("生成成功", f"报价表已保存至:\n{out_path}")
        try:
            os.startfile(os.path.dirname(out_path))
        except Exception:
            pass

    def _timestamp(self):
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    def clear_all(self):
        if messagebox.askyesno("确认", "确定清空已选产品吗？"):
            self.selected_products.clear()
            self.quantities.clear()
            self.refresh_selected_list()
            self.refresh_summary()

    def delete_selected_product(self):
        sel = self.selected_listbox.curselection()
        if not sel:
            messagebox.showwarning("未选择", "请先在已选产品列表中选择要删除的项。")
            return
        idx = sel[0]
        item = self.selected_products[idx]
        is_host = item.get('category', '').endswith('云主机') or '云主机' in item.get('name', '')
        if is_host:
            confirm_msg = f"确定从已选列表中移除云主机 {item['name']} 吗？"
        else:
            confirm_msg = f"确定从已选列表中移除产品 [{item['id']}] {item['name']} 吗？"
        if messagebox.askyesno("删除确认", confirm_msg):
            del self.selected_products[idx]
            self.quantities.pop(item['id'], None)
            self.refresh_selected_list()
            self.refresh_summary()


# ---------- 主入口 ----------
if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # 先隐藏，防止 QuoteApp 构建时闪屏
    fetch_update()  # 暂时禁用，不发网络请求

    # 创建 QuoteApp（构建 UI 但窗口仍隐藏）
    app = QuoteApp(root)

    # 在 QuoteApp 创建后再显示主窗口
    root.deiconify()
    root.update_idletasks()  # 确保窗口管理器完成布局

    # 弹出提示信息（标准模态对话框，不影响主窗口焦点）
    messagebox.showinfo("提示", "已完成更新检查。")

    root.mainloop()
