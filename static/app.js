// ============================================================
// 天翼云等保报价系统 - 前端交互逻辑
// ============================================================

// 状态
let allData = null;                 // products + hosts 数据
let selectedItems = [];            // [{id, name, spec, monthly_price, yearly_price, qty, discount_desc, remark, isHost, category}]

// DOM 引用
const $ = id => document.getElementById(id);
const drawer = $('drawer');
const drawerOverlay = $('drawerOverlay');
const drawerContent = $('drawerContent');
const selectedList = $('selectedList');
const selectedCount = $('selectedCount');
const yearsGroup = $('yearsGroup');
const genBtn = $('genBtn');
const summaryBody = $('summaryBody');

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    // 菜单按钮
    $('menuBtn').addEventListener('click', openDrawer);
    $('drawerClose').addEventListener('click', closeDrawer);
    drawerOverlay.addEventListener('click', closeDrawer);

    // 年数选择
    yearsGroup.addEventListener('click', e => {
        const btn = e.target.closest('.year-btn');
        if (!btn) return;
        yearsGroup.querySelectorAll('.year-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        recalculate();
    });

    // 汇总折叠
    $('summaryToggle').addEventListener('click', () => {
        const isHidden = summaryBody.style.display === 'none';
        summaryBody.style.display = isHidden ? 'block' : 'none';
        $('summaryArrow').textContent = isHidden ? '▾' : '▸';
    });

    // 加载数据
    loadProducts();
});

// ===== 获取当前年数 =====
function getYears() {
    const active = yearsGroup.querySelector('.year-btn.active');
    return active ? parseInt(active.dataset.years) : 1;
}

// ===== 加载产品数据 =====
async function loadProducts() {
    try {
        const resp = await fetch('/api/products');
        allData = await resp.json();
        renderDrawer();
    } catch (err) {
        showToast('加载产品数据失败: ' + err.message);
    }
}

// ===== 渲染抽屉菜单 =====
function renderDrawer() {
    if (!allData) return;
    let html = '';

    // 安全产品
    for (const [cat, products] of Object.entries(allData.categories)) {
        html += `<div class="drawer-section">
            <div class="drawer-section-header" onclick="toggleSection(this)">
                <span>${cat}</span>
                <span class="arrow open">▸</span>
            </div>
            <div class="drawer-section-body open">`;
        for (const p of products) {
            const inCart = selectedItems.find(s => s.id === p.id);
            html += renderProductItem(p, false, inCart);
        }
        html += `</div></div>`;
    }

    // 云主机
    if (allData.hostCategories && Object.keys(allData.hostCategories).length > 0) {
        html += `<div class="drawer-section">
            <div class="drawer-section-header" onclick="toggleSection(this)">
                <span>🖥 云主机（合营池）</span>
                <span class="arrow open">▸</span>
            </div>
            <div class="drawer-section-body open">`;
        for (const [, hosts] of Object.entries(allData.hostCategories)) {
            for (const h of hosts) {
                const inCart = selectedItems.find(s => s.id === h.id);
                html += renderProductItem(h, true, inCart);
            }
        }
        html += `</div></div>`;
    }

    drawerContent.innerHTML = html;
}

function renderProductItem(prod, isHost, inCart) {
    const icon = isHost ? '🖥' : '🔒';
    return `<div class="drawer-prod" data-id="${prod.id}" data-host="${isHost}">
        <div class="drawer-prod-icon">${icon}</div>
        <div class="drawer-prod-info">
            <div class="drawer-prod-name">${prod.name}</div>
            <div class="drawer-prod-price">¥${prod.monthly_price}/月  ¥${prod.yearly_price}/年</div>
        </div>
        <div class="drawer-prod-actions" style="display:flex;align-items:center;gap:4px">
            ${inCart ? `<button class="drawer-prod-sub" onclick="event.stopPropagation();removeItem(${prod.id})">−</button>` : ''}
            <button class="drawer-prod-add" onclick="event.stopPropagation();addItem(${prod.id}, ${isHost})">${inCart ? '✓' : '+'}</button>
        </div>
    </div>`;
}

function toggleSection(header) {
    const body = header.nextElementSibling;
    const arrow = header.querySelector('.arrow');
    const isOpen = body.classList.contains('open');
    body.classList.toggle('open');
    arrow.classList.toggle('open');
}

// ===== 抽屉控制 =====
function openDrawer() {
    drawer.classList.add('open');
    drawerOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeDrawer() {
    drawer.classList.remove('open');
    drawerOverlay.classList.remove('show');
    document.body.style.overflow = '';
}

// ===== 添加产品 =====
function addItem(pid, isHost) {
    const source = isHost ? allData.hostCategories : allData.categories;
    let prod = null;
    if (isHost) {
        for (const [, items] of Object.entries(source)) {
            prod = items.find(i => i.id === pid);
            if (prod) break;
        }
    } else {
        for (const [, items] of Object.entries(source)) {
            prod = items.find(i => i.id === pid);
            if (prod) break;
        }
    }
    if (!prod) return;

    // 检查是否已存在
    if (selectedItems.find(s => s.id === pid)) {
        showToast('该产品已在列表中');
        return;
    }

    selectedItems.push({
        id: prod.id,
        name: prod.name,
        spec: prod.spec,
        monthly_price: prod.monthly_price,
        yearly_price: prod.yearly_price,
        qty: 1,
        discount_desc: prod.discount_desc,
        remark: prod.remark,
        isHost: isHost,
    });

    renderSelectedList();
    recalculate();
    renderDrawer();
    showToast(`已添加 ${prod.name}`);
}

// ===== 移除产品 =====
function removeItem(pid) {
    selectedItems = selectedItems.filter(s => s.id !== pid);
    renderSelectedList();
    recalculate();
    renderDrawer();
}

// ===== 修改数量 =====
function changeQty(pid, delta) {
    const item = selectedItems.find(s => s.id === pid);
    if (!item) return;
    const newQty = item.qty + delta;
    if (newQty < 1) {
        if (confirm(`确定移除 ${item.name} 吗？`)) {
            removeItem(pid);
        }
        return;
    }
    if (newQty > 999) return;
    item.qty = newQty;
    renderSelectedList();
    recalculate();
}

// ===== 渲染已选列表 =====
function renderSelectedList() {
    selectedCount.textContent = selectedItems.length;

    if (selectedItems.length === 0) {
        selectedList.innerHTML = '<div class="empty-hint">请点击左上角 ☰ 添加产品</div>';
        return;
    }

    let html = '';
    for (const item of selectedItems) {
        const hostClass = item.isHost ? ' host' : '';
        html += `<div class="selected-item">
            <div class="selected-item-info">
                <div class="selected-item-name${hostClass}">${item.name}</div>
                <div class="selected-item-price">¥${item.yearly_price}/年</div>
            </div>
            <div class="selected-item-qty">
                <button class="qty-btn minus" onclick="changeQty(${item.id}, -1)">−</button>
                <span class="qty-val">${item.qty}</span>
                <button class="qty-btn plus" onclick="changeQty(${item.id}, 1)">+</button>
            </div>
            <button class="selected-item-remove" onclick="removeItem(${item.id})">✕</button>
        </div>`;
    }
    selectedList.innerHTML = html;
}

// ===== 重新计算 =====
async function recalculate() {
    const years = getYears();
    const sYearLabel = $('sYearLabel');
    const sDiscLabel = $('sDiscLabel');
    sYearLabel.textContent = years;
    sDiscLabel.textContent = years;

    if (selectedItems.length === 0) {
        $('sCount').textContent = '0';
        $('sMonthly').textContent = '¥0.00';
        $('sYearlyTotal').textContent = '¥0.00';
        $('sDiscounted').textContent = '¥0.00';
        $('s45').textContent = '¥0.00';
        $('s55').textContent = '¥0.00';
        genBtn.textContent = '📄 生成报价';
        return;
    }

    try {
        const payload = {
            items: selectedItems.map(s => ({ id: s.id, qty: s.qty })),
            years: years,
        };
        const resp = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await resp.json();

        if (result.error) {
            showToast(result.error);
            return;
        }

        $('sCount').textContent = result.count;
        $('sMonthly').textContent = '¥' + fmt(result.totals.monthly);
        $('sYearlyTotal').textContent = '¥' + fmt(result.totals.yearlyTotal);
        $('sDiscounted').textContent = '¥' + fmt(result.totals.discountedTotal);
        $('s45').textContent = '¥' + fmt(result.totals.price_45);
        $('s55').textContent = '¥' + fmt(result.totals.price_55);
        genBtn.textContent = '📄 生成报价（' + years + '年）';
    } catch (err) {
        showToast('计算失败: ' + err.message);
    }
}

// ===== 生成报价 =====
async function generateQuote() {
    if (selectedItems.length === 0) {
        showToast('请先选择产品');
        return;
    }

    const years = getYears();
    genBtn.disabled = true;
    genBtn.textContent = '⏳ 生成中...';

    try {
        const payload = {
            items: selectedItems.map(s => ({ id: s.id, qty: s.qty })),
            years: years,
        };
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const err = await resp.json();
            showToast(err.error || '生成失败');
            genBtn.disabled = false;
            genBtn.textContent = '📄 生成报价';
            return;
        }

        // 下载文件
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = getFilename(resp);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('报价表已生成并下载');
    } catch (err) {
        showToast('生成失败: ' + err.message);
    } finally {
        genBtn.disabled = false;
        genBtn.textContent = '📄 生成报价';
    }
}

// ===== 清空全部 =====
function clearAll() {
    if (selectedItems.length === 0) return;
    if (!confirm('确定清空全部已选产品吗？')) return;
    selectedItems = [];
    renderSelectedList();
    recalculate();
    renderDrawer();
    showToast('已清空全部');
}

// ===== 辅助函数 =====
function fmt(n) {
    return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getFilename(resp) {
    const cd = resp.headers.get('Content-Disposition');
    if (cd) {
        const match = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match) return match[1].replace(/['"]/g, '');
    }
    return '天翼云等保专区安全产品报价表.xlsx';
}

let toastTimer = null;
function showToast(msg) {
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2000);
}