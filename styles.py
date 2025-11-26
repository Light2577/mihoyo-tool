# styles.py

# 优先使用现代字体
BASE_FONT = '"Segoe UI Variable Display", "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'

# 现代极简风配色 - 亮色
LIGHT_THEME = f"""
    /* 全局重置 */
    QWidget {{
        font-family: {BASE_FONT};
        outline: none;
    }}

    /* 主窗口容器 */
    QWidget#MainWidget {{
        background: #FFFFFF;
        border: 1px solid #F3F4F6;
        border-radius: 24px;
    }}

    /* 标题文字 */
    QLabel#TitleLabel {{
        font-size: 16px;
        font-weight: 700;
        color: #1F2937;
    }}

    /* 状态卡片 */
    QWidget#StatusCard {{
        background-color: #F9FAFB;
        border-radius: 16px;
        border: none; 
    }}
    QLabel#StatusLabel {{
        font-size: 20px;
        font-weight: 700;
        color: #3B82F6; 
    }}

    /* 进度条 */
    QProgressBar {{
        background: #E5E7EB;
        border: none;
        border-radius: 8px;
        height: 16px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #3B82F6);
        border-radius: 8px;
    }}

    /* 窗口控制按钮 */
    QPushButton#WinCtrlBtn, QPushButton#CloseBtn {{
        background: transparent;
        border: none;
        border-radius: 8px;
    }}
    QPushButton#WinCtrlBtn:hover {{ background-color: #F3F4F6; }}
    QPushButton#WinCtrlBtn:checked {{ color: #3B82F6; }}
    QPushButton#CloseBtn:hover {{ background-color: #FEE2E2; color: #EF4444; }}

    /* 主按钮 (开始) - 胶囊 */
    QPushButton#StartBtn {{
        background-color: #3B82F6;
        color: white;
        border: none;
        border-radius: 20px; 
        font-weight: 600;
        font-size: 14px;
        padding: 0 24px;
    }}
    QPushButton#StartBtn:hover {{ background-color: #2563EB; }}
    QPushButton#StartBtn:pressed {{ background-color: #1D4ED8; margin-top: 1px; }}
    QPushButton#StartBtn:disabled {{ background-color: #E5E7EB; color: #9CA3AF; }}

    /* 次按钮 (停止) - 胶囊 */
    QPushButton#StopBtn {{
        background-color: #F3F4F6;
        color: #4B5563;
        border: none;
        border-radius: 20px;
        font-weight: 600;
        font-size: 14px;
    }}
    QPushButton#StopBtn:hover {{ background-color: #E5E7EB; color: #111827; }}
    QPushButton#StopBtn:pressed {{ background-color: #D1D5DB; }}
"""

# 暗色模式
DARK_THEME = f"""
    QWidget {{
        font-family: {BASE_FONT};
        outline: none;
        color: #E5E7EB;
    }}
    QWidget#MainWidget {{
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 24px;
    }}
    QLabel#TitleLabel {{ color: #F9FAFB; }}

    QWidget#StatusCard {{
        background-color: #1F2937;
        border-radius: 16px;
    }}
    QLabel#StatusLabel {{ color: #60A5FA; }}

    QProgressBar {{ background: #374151; border-radius: 8px; height: 16px; }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #3B82F6);
        border-radius: 8px;
    }}

    QPushButton#WinCtrlBtn:hover {{ background-color: #374151; }}
    QPushButton#WinCtrlBtn:checked {{ color: #60A5FA; }}
    QPushButton#CloseBtn:hover {{ background-color: #991B1B; }}

    QPushButton#StartBtn {{
        background-color: #3B82F6;
        color: #FFFFFF;
        border-radius: 20px;
        border: none;
    }}
    QPushButton#StartBtn:hover {{ background-color: #2563EB; }}
    QPushButton#StartBtn:disabled {{ background-color: #1F2937; color: #4B5563; }}

    QPushButton#StopBtn {{
        background-color: #1F2937;
        color: #9CA3AF;
        border-radius: 20px;
        border: none;
    }}
    QPushButton#StopBtn:hover {{ background-color: #374151; color: #F3F4F6; }}
"""

THEMES = {"light": LIGHT_THEME, "dark": DARK_THEME}
