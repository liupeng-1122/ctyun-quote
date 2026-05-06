# -*- coding: utf-8 -*-
"""
天翼云等保报价系统 - Android 入口
启动 Flask 服务器 + 打开 WebView
"""
import os
import sys
import threading
import time

# 确保可导入项目模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ---------- 后台启动 Flask ----------
def start_flask():
    """在后台线程中启动 Flask 服务器"""
    from app import app
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    # 启动 Flask 服务器（后台线程）
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    time.sleep(1.5)  # 等待服务器就绪

    # 在 WebView 中加载 Flask 页面
    try:
        from android.webview import AndroidWebView
        webview = AndroidWebView()
        webview.load_url('http://127.0.0.1:5000')
        webview.show()
        # 保持主线程存活
        while True:
            time.sleep(1)
    except ImportError:
        # 本地测试环境：直接启动 Flask（非 WebView 模式）
        print("[手机端] 将以 WebView 模式运行")
        print("[PC端]   将以 Flask 服务器模式运行")
        start_flask()