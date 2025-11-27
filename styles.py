# styles.py

# 优先使用现代字体
BASE_FONT = '"Manrope", "Segoe UI Variable Display", "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'

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
        font-size: 17px;
        font-weight: 800;
        color: #1F2937;
    }}

    /* 状态卡片 */
    QWidget#StatusCard {{
        background-color: #F9FAFB;
        border-radius: 16px;
        border: none; 
    }}
    QWidget#ControlCard {{
        background-color: #F7FBFF;
        border: 1px solid #E0E7FF;
        border-radius: 16px;
    }}
    QLabel#StatusLabel {{
        font-size: 19px;
        font-weight: 800;
        color: #3B82F6; 
    }}
    /* 进度条 */
    QProgressBar {{
        background: #E5E7EB;
        border: none;
        border-radius: 8px;
        height: 18px;
        font-size: 11px;
        font-weight: 800;
        color: #0F172A;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BFDBFE, stop:1 #60A5FA);
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
        background-color: #E8F1FF;
        color: #1D4ED8;
        border: 1px solid #C7D7F7;
        border-radius: 16px; 
        font-weight: 800;
        font-size: 15px;
        padding: 0 18px;
    }}
    QPushButton#StartBtn:hover {{ background-color: #D8E8FF; border-color: #A7C3F3; }}
    QPushButton#StartBtn:pressed {{ background-color: #C7D7F7; border-color: #93B4EF; margin-top: 1px; }}
    QPushButton#StartBtn:disabled {{ background-color: #F3F4F6; color: #9CA3AF; border-color: #E5E7EB; }}

    /* 继续按钮 */
    QPushButton#ContinueBtn {{
        background-color: #ECFDF3;
        color: #047857;
        border: 1px solid #C6F6D5;
        border-radius: 14px;
        font-weight: 800;
        font-size: 15px;
        padding: 0 16px;
    }}
    QPushButton#ContinueBtn:hover {{ background-color: #DFF9E8; border-color: #A7F3D0; }}
    QPushButton#ContinueBtn:pressed {{ background-color: #C6F6D5; border-color: #86EFAC; margin-top: 1px; }}
    QPushButton#ContinueBtn:disabled {{ background-color: #F3F4F6; color: #9CA3AF; border-color: #E5E7EB; }}
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
        background-color: #111827;
        border-radius: 16px;
    }}
    QWidget#ControlCard {{
        background-color: #0B1220;
        border: 1px solid #1F2937;
        border-radius: 16px;
    }}
    QLabel#StatusLabel {{ color: #93C5FD; font-size: 19px; font-weight: 800; }}
    QProgressBar {{ background: #1F2937; border-radius: 8px; height: 18px; font-size: 11px; font-weight: 800; color: #E5E7EB; }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
        border-radius: 8px;
    }}

    QPushButton#WinCtrlBtn:hover {{ background-color: #374151; }}
    QPushButton#WinCtrlBtn:checked {{ color: #60A5FA; }}
    QPushButton#CloseBtn:hover {{ background-color: #991B1B; }}

    QPushButton#StartBtn {{
        background-color: #1F2A44;
        color: #93C5FD;
        border-radius: 16px;
        border: 1px solid #243B61;
        font-weight: 800;
        font-size: 15px;
    }}
    QPushButton#StartBtn:hover {{ background-color: #233357; border-color: #2F4B7A; }}
    QPushButton#StartBtn:disabled {{ background-color: #1F2937; color: #4B5563; border-color: #1F2937; }}

    QPushButton#ContinueBtn {{
        background-color: #122B23;
        color: #6EE7B7;
        border-radius: 14px;
        border: 1px solid #1C3F32;
        font-weight: 800;
        font-size: 15px;
    }}
    QPushButton#ContinueBtn:hover {{ background-color: #163429; border-color: #1E4B39; }}
    QPushButton#ContinueBtn:disabled {{ background-color: #1F2937; color: #4B5563; border-color: #1F2937; }}
"""

THEMES = {"light": LIGHT_THEME, "dark": DARK_THEME}
