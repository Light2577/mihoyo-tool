<div align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&pause=1000&color=F7F7F7&background=00000000&center=true&vCenter=true&width=435&lines=miHoYo+Tool;专治各种“禁止粘贴”;模拟人工手打;安全、开源、高效" alt="Typing SVG" />
</div>

<div align="center">

![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## ⚡ 这是什么？

**miHoYo Tool** 是一款专为解决“禁止粘贴”烦恼而生的生产力工具。

有些网页（如网银、考试系统）、远程桌面或企业软件**禁止使用 `Ctrl+V`**。本工具能读取你剪贴板里的内容，在底层模拟物理键盘信号，通过**“模拟打字”**的方式帮你把内容输进去。

> 🚀 **你的自动化打字员。**

---

## 📺 效果演示 (Demo)


<div align="center">
  <img src="assets/demo.svg" width="100%" alt="miHoYo Tool UI Demo">
</div>


---

## 🚀 怎么用 (Quick Start)

1.  **📥 下载**：前往 [Releases](../../releases) 下载最新版 `miHoYo Tool.exe`。
2.  **🛡️ 运行**：右键选择 **“以管理员身份运行”**（重要！没有权限无法模拟按键）。
3.  **📋 复制**：正常复制你要输入的文字 (`Ctrl+C`)。
4.  **🖱️ 聚焦**：点一下你要输入的文本框（网页、游戏、软件均可）。
5.  **Go**：按下热键 **`F9`**，开始自动打字！

---

## ⚙️ 功能特性

| 功能 | 说明 |
| :--- | :--- |
| **🎹 剪贴板直通** | 自动读取剪贴板，智能处理换行符 |
| **🕹️ 全局热键** | 默认 **F9** 开始，**F10** 停止 (支持自定义) |
| **🐢 拟人化延迟** | 支持设置输入间隔和随机浮动，防止被检测为脚本 |
| **🎨 现代 UI** | 基于 PySide6 的无边框设计，支持 Win11 动画 |

---

## 🛠️ 本地构建 (Build)

如果你想自己修改源码：

```bash
# 1. 克隆项目
git clone [https://github.com/Light2577/mihoyo-tool.git](https://github.com/Light2577/mihoyo-tool.git)

# 2. 安装依赖
pip install pyside6 nuitka zstandard

# 3. 一键打包
python -m nuitka --standalone --onefile --enable-plugin=pyside6 --windows-console-mode=disable --windows-uac-admin --windows-icon-from-ico=icon.ico --output-filename="miHoYo Tool.exe" --output-dir=dist main.py
