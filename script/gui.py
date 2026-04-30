#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyQt 主窗口模块
提供应用程序的主界面，包含现代化深色主题 UI（中文版）
"""

import json
import sys
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QObject
from PyQt6.QtGui import QAction, QFont, QIcon, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QFrame,
    QStackedWidget, QStatusBar, QMenuBar, QToolBar, QMessageBox,
    QProgressBar, QFileDialog, QScrollArea, QSizePolicy, QGroupBox,
    QSpacerItem, QButtonGroup, QGraphicsDropShadowEffect, QMenu
)

from script.config_manager import get_config_manager, ConfigManager
from script.network import HttpClient, HttpResponse
from script.paths import APP_DIR, CONFIG_DIR, OUTPUT_DIR, INPUT_DIR
from script.utils import open_folder, format_json, safe_json_loads
from script.logger import get_logger


# ============================================================================
# Windows DWM API 支持（用于窗口圆角）
# ============================================================================

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    # DWM 窗口属性
    DWMWA_WINDOW_CORNER_PREFERENCE = 33

    # 圆角偏好 (Windows 11)
    DWMWCP_DEFAULT = 0
    DWMWCP_ROUND = 2

    # 加载 Windows API
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

    dwmapi.DwmSetWindowAttribute.restype = ctypes.c_int
    dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]


# ============================================================================
# 自绘标题栏（VSCode左侧 + Cherry右侧拼接风格）
# ============================================================================

class TitleBarButton(QPushButton):
    """标题栏按钮基类，支持悬停高亮"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "title-menu-btn")


class TitleBar(QWidget):
    """
    自绘标题栏

    布局结构（从左到右）：
    [应用标题] [标题工具栏] [stretch拖拽区] [主题pill] [设置] [窗口控制按钮]
    """

    # 信号
    theme_clicked = pyqtSignal(str)  # 'dark' 或 'light'
    settings_clicked = pyqtSignal()

    # 统一高度常量
    HEIGHT = 36

    def __init__(self, parent: Optional[QMainWindow] = None):
        super().__init__(parent)
        self.parent_window = parent
        self.pressing = False
        self.start_pos = QPoint()
        self._current_theme = 'dark'

        self.setFixedHeight(self.HEIGHT)
        self.setProperty("class", "title-bar")
        self.setAutoFillBackground(True)

        self.setup_ui()

    def setup_ui(self) -> None:
        """设置标题栏布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        # ========== 应用标题（固定宽度）==========
        self.title_label = QLabel("PyQt EXE 模板")
        self.title_label.setProperty("class", "title-text")
        self.title_label.setCursor(Qt.CursorShape.ArrowCursor)
        layout.addWidget(self.title_label)
        layout.addSpacing(12)

        # ========== 标题工具栏（紧凑排列，不拉伸）==========
        self.title_toolbar = self._create_title_toolbar()
        layout.addWidget(self.title_toolbar)

        # ========== 拖拽空白区域（stretch）==========
        layout.addStretch(1)

        # ========== 右侧控制区 ==========
        self.right_controls = self._create_right_controls()
        layout.addWidget(self.right_controls)

        # 初始化按钮状态
        self.update_theme_state('dark')

    # =========================================================================
    # 标题工具栏配置与创建
    # =========================================================================

    def _get_title_toolbar_items(self) -> list:
        """
        获取标题工具栏配置项

        Returns:
            list: 工具栏项配置列表，每项包含：
                - key: 唯一标识
                - text: 显示文本
                - menu_items: 菜单项列表（可选）

        说明：
            此方法返回的配置决定标题工具栏的内容。
            项目基础模板中使用示例菜单，实际项目可覆盖此方法或修改配置。
        """
        return [
            {
                "key": "file",
                "text": "文件(F)",
                "menu_items": [
                    {"text": "新建项目", "shortcut": "Ctrl+N", "callback": "_action_new_project"},
                    {"text": "打开项目", "shortcut": "Ctrl+O", "callback": "_action_open_project"},
                    {"separator": True},
                    {"text": "保存", "shortcut": "Ctrl+S", "callback": "_action_save"},
                    {"text": "另存为...", "shortcut": "Ctrl+Shift+S", "callback": "_action_save_as"},
                    {"separator": True},
                    {"text": "退出", "shortcut": "Alt+F4", "callback": "_on_close"},
                ]
            },
            {
                "key": "edit",
                "text": "编辑(E)",
                "menu_items": [
                    {"text": "撤销", "shortcut": "Ctrl+Z", "callback": "_action_undo"},
                    {"text": "重做", "shortcut": "Ctrl+Y", "callback": "_action_redo"},
                    {"separator": True},
                    {"text": "剪切", "shortcut": "Ctrl+X", "callback": "_action_cut"},
                    {"text": "复制", "shortcut": "Ctrl+C", "callback": "_action_copy"},
                    {"text": "粘贴", "shortcut": "Ctrl+V", "callback": "_action_paste"},
                ]
            },
            {
                "key": "selection",
                "text": "选择(S)",
                "menu_items": [
                    {"text": "全选", "shortcut": "Ctrl+A", "callback": "_action_select_all"},
                    {"text": "取消选择", "shortcut": "", "callback": "_action_deselect"},
                    {"separator": True},
                    {"text": "查找", "shortcut": "Ctrl+F", "callback": "_action_find"},
                    {"text": "替换", "shortcut": "Ctrl+H", "callback": "_action_replace"},
                ]
            },
            {
                "key": "view",
                "text": "查看(V)",
                "menu_items": [
                    {"text": "放大", "shortcut": "Ctrl++", "callback": "_action_zoom_in"},
                    {"text": "缩小", "shortcut": "Ctrl+-", "callback": "_action_zoom_out"},
                    {"text": "重置缩放", "shortcut": "Ctrl+0", "callback": "_action_zoom_reset"},
                    {"separator": True},
                    {"text": "全屏", "shortcut": "F11", "callback": "_action_fullscreen"},
                ]
            },
        ]

    def _create_title_toolbar(self) -> QWidget:
        """
        创建标题工具栏

        Returns:
            QWidget: 包含工具按钮的容器，使用固定宽度策略
        """
        toolbar = QWidget()
        toolbar.setProperty("class", "title-toolbar")
        toolbar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(2)

        for item in self._get_title_toolbar_items():
            btn = self._create_toolbar_button(item)
            toolbar_layout.addWidget(btn)

        return toolbar

    def _create_toolbar_button(self, item: dict) -> QPushButton:
        """
        创建单个工具栏按钮

        Args:
            item: 工具栏项配置

        Returns:
            QPushButton: 配置好的按钮
        """
        text = item.get("text", "")
        btn = QPushButton(text)
        btn.setProperty("class", "title-menu-btn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # 计算按钮宽度：文字宽度 + 左右 padding
        text_width = btn.fontMetrics().horizontalAdvance(text)
        btn.setFixedWidth(text_width + 20)
        btn.setFixedHeight(28)

        # 创建菜单
        menu = self._create_menu_from_items(item.get("menu_items", []))
        menu.setParent(self)
        btn.setMenu(menu)

        return btn

    def _create_menu_from_items(self, menu_items: list) -> QMenu:
        """
        根据配置创建菜单

        Args:
            menu_items: 菜单项配置列表

        Returns:
            QMenu: 创建好的菜单
        """
        menu = QMenu(self)

        for item in menu_items:
            if item.get("separator"):
                menu.addSeparator()
                continue

            action = QAction(item.get("text", ""), self)
            shortcut = item.get("shortcut", "")
            if shortcut:
                action.setShortcut(shortcut)

            callback_name = item.get("callback")
            if callback_name and hasattr(self, callback_name):
                action.triggered.connect(getattr(self, callback_name))

            menu.addAction(action)

        return menu

    # =========================================================================
    # 右侧控制区创建
    # =========================================================================

    def _create_right_controls(self) -> QWidget:
        """创建右侧控制区（主题、设置、窗口控制按钮）"""
        controls = QWidget()
        controls.setProperty("class", "title-controls")
        controls.setFixedHeight(self.HEIGHT)

        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        btn_size = self.HEIGHT - 8

        # pill 按钮容器
        pill_container = QFrame()
        pill_container.setProperty("class", "title-pill-container")
        pill_layout = QHBoxLayout(pill_container)
        pill_layout.setContentsMargins(6, 4, 6, 4)
        pill_layout.setSpacing(4)

        # 深色主题按钮
        self.dark_btn = QPushButton()
        self.dark_btn.setProperty("class", "title-pill-btn")
        self.dark_btn.setText("🌙")
        self.dark_btn.setCheckable(True)
        self.dark_btn.setFixedSize(btn_size, btn_size)
        self.dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_btn.setToolTip("深色主题")
        self.dark_btn.clicked.connect(lambda: self._on_theme_click('dark'))
        pill_layout.addWidget(self.dark_btn)

        # 浅色主题按钮
        self.light_btn = QPushButton()
        self.light_btn.setProperty("class", "title-pill-btn")
        self.light_btn.setText("☀️")
        self.light_btn.setCheckable(True)
        self.light_btn.setFixedSize(btn_size, btn_size)
        self.light_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.light_btn.setToolTip("浅色主题")
        self.light_btn.clicked.connect(lambda: self._on_theme_click('light'))
        pill_layout.addWidget(self.light_btn)

        layout.addWidget(pill_container)

        # 分隔符
        separator1 = QFrame()
        separator1.setProperty("class", "title-separator")
        separator1.setFixedSize(1, int(self.HEIGHT * 0.6))
        layout.addWidget(separator1)
        layout.addSpacing(4)

        # 设置按钮
        self.settings_btn = QPushButton()
        self.settings_btn.setProperty("class", "title-icon-btn")
        self.settings_btn.setText("⚙️")
        self.settings_btn.setFixedSize(btn_size, btn_size)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self.settings_btn)

        # 分隔符
        separator2 = QFrame()
        separator2.setProperty("class", "title-separator")
        separator2.setFixedSize(1, int(self.HEIGHT * 0.6))
        layout.addWidget(separator2)
        layout.addSpacing(4)

        # 窗口控制按钮
        win_btn_size = self.HEIGHT

        self.minimize_btn = QPushButton()
        self.minimize_btn.setProperty("class", "title-win-btn")
        self.minimize_btn.setText("─")
        self.minimize_btn.setFixedSize(win_btn_size, win_btn_size)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.setToolTip("最小化")
        self.minimize_btn.clicked.connect(self._on_minimize)
        layout.addWidget(self.minimize_btn)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setProperty("class", "title-win-btn")
        self.maximize_btn.setText("□")
        self.maximize_btn.setFixedSize(win_btn_size, win_btn_size)
        self.maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximize_btn.setToolTip("最大化")
        self.maximize_btn.clicked.connect(self._on_maximize)
        layout.addWidget(self.maximize_btn)

        self.close_btn = QPushButton()
        self.close_btn.setProperty("class", "title-win-btn title-close-btn")
        self.close_btn.setText("✕")
        self.close_btn.setFixedSize(win_btn_size, win_btn_size)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self._on_close)
        layout.addWidget(self.close_btn)

        return controls

    # =========================================================================
    # 事件处理与工具方法
    # =========================================================================

    def _on_theme_click(self, theme: str) -> None:
        """主题按钮点击"""
        self.theme_clicked.emit(theme)

    def _on_minimize(self) -> None:
        """最小化窗口"""
        if self.parent_window:
            self.parent_window.showMinimized()

    def _on_maximize(self) -> None:
        """最大化/还原窗口"""
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_btn.setText("□")
                self.maximize_btn.setToolTip("最大化")
            else:
                self.parent_window.showMaximized()
                self.maximize_btn.setText("❐")
                self.maximize_btn.setToolTip("还原")

    def _on_close(self) -> None:
        """关闭窗口"""
        if self.parent_window:
            self.parent_window.close()

    def update_theme_state(self, theme: str) -> None:
        """更新主题按钮状态"""
        self._current_theme = theme
        self.dark_btn.setChecked(theme == 'dark')
        self.light_btn.setChecked(theme == 'light')

    def set_title(self, title: str) -> None:
        """设置标题"""
        self.title_label.setText(title)

    # =========================================================================
    # 菜单动作占位方法（实际项目可替换为真实逻辑）
    # =========================================================================

    def _action_new_project(self): pass
    def _action_open_project(self): pass
    def _action_save(self): pass
    def _action_save_as(self): pass
    def _action_undo(self): pass
    def _action_redo(self): pass
    def _action_cut(self): pass
    def _action_copy(self): pass
    def _action_paste(self): pass
    def _action_select_all(self): pass
    def _action_deselect(self): pass
    def _action_find(self): pass
    def _action_replace(self): pass
    def _action_zoom_in(self): pass
    def _action_zoom_out(self): pass
    def _action_zoom_reset(self): pass
    def _action_fullscreen(self): pass

    # =========================================================================
    # 窗口拖拽处理
    # =========================================================================

    def mousePressEvent(self, event) -> None:
        if self._is_in_drag_area(event.pos()):
            if event.button() == Qt.MouseButton.LeftButton:
                self.pressing = True
                self.start_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.pressing and self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_btn.setText("□")
                self.maximize_btn.setToolTip("最大化")
            end_pos = event.globalPosition().toPoint()
            move = end_pos - self.start_pos
            new_pos = self.parent_window.pos() + move
            self.parent_window.move(new_pos)
            self.start_pos = end_pos
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.pressing = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._is_in_drag_area(event.pos()):
            self._on_maximize()
        super().mouseDoubleClickEvent(event)

    def _is_in_drag_area(self, pos: QPoint) -> bool:
        """检查位置是否在拖拽区域内"""
        return pos.x() < self.right_controls.geometry().left()


# ============================================================================
# HTTP 请求工作线程
# ============================================================================

class HttpRequestWorker(QThread):
    """HTTP 请求后台工作线程"""
    
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
        timeout: int = 30
    ):
        super().__init__()
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.body = body
        self.timeout = timeout
        self._is_cancelled = False
    
    def run(self) -> None:
        """执行 HTTP 请求"""
        try:
            client = HttpClient(timeout=self.timeout)
            
            json_data = None
            if self.body and self.method in ('POST', 'PUT', 'PATCH'):
                try:
                    json_data = json.loads(self.body)
                except json.JSONDecodeError:
                    pass
            
            response: HttpResponse
            
            if self.method == 'GET':
                response = client.get(self.url, headers=self.headers, timeout=self.timeout)
            elif self.method == 'POST':
                response = client.post(self.url, json_data=json_data, headers=self.headers, timeout=self.timeout)
            elif self.method == 'PUT':
                response = client.put(self.url, json_data=json_data, headers=self.headers, timeout=self.timeout)
            elif self.method == 'DELETE':
                response = client.delete(self.url, headers=self.headers, timeout=self.timeout)
            else:
                response = client.request(self.method, self.url, headers=self.headers, json_data=json_data, timeout=self.timeout)
            
            if not self._is_cancelled:
                self.finished.emit(response)
                
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
    
    def cancel(self) -> None:
        """取消请求"""
        self._is_cancelled = True


# ============================================================================
# 导航按钮
# ============================================================================

class NavButton(QPushButton):
    """自定义导航按钮"""
    
    def __init__(self, text: str, icon_text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}" if icon_text else f"    {text}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "nav-button")
        self.setFixedHeight(36)


# ============================================================================
# 卡片组件
# ============================================================================

class CardWidget(QFrame):
    """卡片组件"""
    
    def __init__(self, title: str = "", description: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setup_ui(title, description)
    
    def setup_ui(self, title: str, description: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        if title:
            title_label = QLabel(title)
            title_label.setProperty("class", "card-title")
            title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
            layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setProperty("class", "card-description")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)


# ============================================================================
# Dashboard 首页
# ============================================================================

class DashboardPage(QWidget):
    """Dashboard 首页"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 欢迎标题
        welcome_label = QLabel("欢迎使用 PyQt EXE 模板")
        welcome_label.setProperty("class", "page-title")
        welcome_label.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        layout.addWidget(welcome_label)

        subtitle = QLabel("一个现代化的 PyQt6 桌面应用程序模板，内置 HTTP 客户端支持")
        subtitle.setProperty("class", "page-subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        # 功能卡片区域
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        card1 = CardWidget("🎨 PyQt6 界面", "现代深色主题，QSS 样式")
        cards_layout.addWidget(card1)

        card2 = CardWidget("🌐 HTTP 客户端", "内置 HTTP 请求测试工具")
        cards_layout.addWidget(card2)

        card3 = CardWidget("⚙️ 配置管理", "基于 YAML 的配置系统")
        cards_layout.addWidget(card3)

        card4 = CardWidget("📦 PyInstaller", "轻松打包 Windows EXE")
        cards_layout.addWidget(card4)

        layout.addLayout(cards_layout)

        layout.addSpacing(12)

        # 快捷操作区域
        actions_label = QLabel("快捷操作")
        actions_label.setProperty("class", "section-title")
        actions_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        layout.addWidget(actions_label)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        self.open_config_btn = QPushButton("📁 打开配置目录")
        self.open_config_btn.setProperty("class", "action-button")
        self.open_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.open_config_btn)
        
        self.open_output_btn = QPushButton("📂 打开输出目录")
        self.open_output_btn.setProperty("class", "action-button")
        self.open_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.open_output_btn)
        
        self.test_http_btn = QPushButton("🚀 测试 HTTP 请求")
        self.test_http_btn.setProperty("class", "action-button")
        self.test_http_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.test_http_btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        layout.addStretch()


# ============================================================================
# HTTP Client 页面
# ============================================================================

class HttpClientPage(QWidget):
    """HTTP 请求测试页面"""
    
    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.worker: Optional[HttpRequestWorker] = None
        self.setup_ui()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 页面标题
        title = QLabel("HTTP 客户端")
        title.setProperty("class", "page-title")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel("测试 HTTP 请求，支持自定义请求头和请求体")
        desc.setProperty("class", "page-subtitle")
        layout.addWidget(desc)

        layout.addSpacing(8)

        # URL 和 Method 行
        url_layout = QHBoxLayout()

        method_label = QLabel("方法：")
        method_label.setFixedWidth(50)
        url_layout.addWidget(method_label)

        self.method_combo = QComboBox()
        self.method_combo.addItems(['GET', 'POST', 'PUT', 'DELETE'])
        self.method_combo.setFixedWidth(80)
        url_layout.addWidget(self.method_combo)

        url_label = QLabel("URL：")
        url_label.setFixedWidth(35)
        url_layout.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入 URL...")
        default_url = self.config_manager.get('network.default_url', 'https://httpbin.org/get')
        self.url_input.setText(default_url)
        url_layout.addWidget(self.url_input)

        layout.addLayout(url_layout)

        # Headers 输入
        headers_label = QLabel("请求头 (JSON)：")
        layout.addWidget(headers_label)

        self.headers_input = QTextEdit()
        self.headers_input.setPlaceholderText('{\n  "Content-Type": "application/json"\n}')
        self.headers_input.setMaximumHeight(50)
        self.headers_input.setFont(QFont("Consolas", 9))
        layout.addWidget(self.headers_input)

        # Body 输入
        self.body_label = QLabel("请求体 (JSON)：")
        layout.addWidget(self.body_label)

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText('{\n  "key": "value"\n}')
        self.body_input.setMaximumHeight(60)
        self.body_input.setFont(QFont("Consolas", 9))
        layout.addWidget(self.body_input)
        
        # 发送按钮
        btn_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("发送请求")
        self.send_btn.setProperty("class", "primary-button")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_request)
        btn_layout.addWidget(self.send_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setProperty("class", "secondary-button")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_response)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 响应区域
        response_label = QLabel("响应：")
        layout.addWidget(response_label)
        
        # 状态信息行
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("状态：-")
        self.status_label.setProperty("class", "status-label")
        status_layout.addWidget(self.status_label)
        
        self.time_label = QLabel("耗时：-")
        self.time_label.setProperty("class", "time-label")
        status_layout.addWidget(self.time_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 响应内容
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setFont(QFont("Consolas", 9))
        self.response_output.setPlaceholderText("响应内容将显示在这里...")
        layout.addWidget(self.response_output)
    
    def send_request(self) -> None:
        """发送 HTTP 请求"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入 URL")
            return
        
        method = self.method_combo.currentText()
        headers_text = self.headers_input.toPlainText().strip()
        body_text = self.body_input.toPlainText().strip()
        
        headers = {}
        if headers_text:
            headers = safe_json_loads(headers_text, {})
            if headers is None:
                QMessageBox.warning(self, "警告", "请求头 JSON 格式无效")
                return
        
        timeout = self.config_manager.get('network.timeout', 30)
        
        self.send_btn.setEnabled(False)
        self.send_btn.setText("发送中...")
        self.status_label.setText("状态：发送中...")
        
        self.worker = HttpRequestWorker(
            method=method,
            url=url,
            headers=headers,
            body=body_text if method in ('POST', 'PUT', 'PATCH') else None,
            timeout=timeout
        )
        self.worker.finished.connect(self.on_request_finished)
        self.worker.error.connect(self.on_request_error)
        self.worker.start()
    
    def on_request_finished(self, response: HttpResponse) -> None:
        """请求完成回调"""
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送请求")
        
        status_color = "#22C55E" if response.success else "#EF4444"
        self.status_label.setText(f"状态：{response.status_code}")
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        
        self.time_label.setText(f"耗时：{response.elapsed_ms:.0f} 毫秒")
        
        if response.data is not None:
            formatted = format_json(response.data)
            self.response_output.setPlainText(formatted)
        else:
            self.response_output.setPlainText(response.text or "(空响应)")
        
        if not response.success:
            self.response_output.append(f"\n\n--- 错误 ---\n{response.message}")
    
    def on_request_error(self, error: str) -> None:
        """请求错误回调"""
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送请求")
        
        self.status_label.setText("状态：错误")
        self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.time_label.setText("耗时：-")
        
        self.response_output.setPlainText(f"请求失败：\n{error}")
    
    def clear_response(self) -> None:
        """清空响应"""
        self.response_output.clear()
        self.status_label.setText("状态：-")
        self.status_label.setStyleSheet("")
        self.time_label.setText("耗时：-")


# ============================================================================
# Settings 页面
# ============================================================================

class SettingsPage(QWidget):
    """设置页面"""

    # 主题切换信号
    theme_changed = pyqtSignal(str)

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._theme_updating = False  # 防止循环更新
        self.setup_ui()
        self.load_settings()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 页面标题
        title = QLabel("设置")
        title.setProperty("class", "page-title")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel("配置应用程序设置")
        desc.setProperty("class", "page-subtitle")
        layout.addWidget(desc)

        layout.addSpacing(8)

        # 外观设置组
        appearance_group = QGroupBox("外观")
        appearance_group.setProperty("class", "settings-group")
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setSpacing(12)

        # 主题切换标签
        theme_label = QLabel("主题：")
        appearance_layout.addWidget(theme_label)

        # 主题切换按钮容器
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(10)

        # 创建按钮组（互斥）
        self.theme_btn_group = QButtonGroup(self)
        self.theme_btn_group.setExclusive(True)

        # 深色主题按钮
        self.dark_theme_btn = QPushButton("🌙 深色")
        self.dark_theme_btn.setProperty("class", "theme-btn")
        self.dark_theme_btn.setCheckable(True)
        self.dark_theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_theme_btn.clicked.connect(lambda: self._on_theme_btn_click("dark"))
        self.theme_btn_group.addButton(self.dark_theme_btn, 0)
        theme_btn_layout.addWidget(self.dark_theme_btn)

        # 浅色主题按钮
        self.light_theme_btn = QPushButton("☀️ 浅色")
        self.light_theme_btn.setProperty("class", "theme-btn")
        self.light_theme_btn.setCheckable(True)
        self.light_theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.light_theme_btn.clicked.connect(lambda: self._on_theme_btn_click("light"))
        self.theme_btn_group.addButton(self.light_theme_btn, 1)
        theme_btn_layout.addWidget(self.light_theme_btn)

        theme_btn_layout.addStretch()
        appearance_layout.addLayout(theme_btn_layout)

        layout.addWidget(appearance_group)

        # 应用设置组
        app_group = QGroupBox("应用程序")
        app_group.setProperty("class", "settings-group")
        app_layout = QVBoxLayout(app_group)
        app_layout.setSpacing(6)

        # App Name
        name_layout = QHBoxLayout()
        name_label = QLabel("应用名称：")
        name_label.setFixedWidth(85)
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        app_layout.addLayout(name_layout)

        # App Version
        version_layout = QHBoxLayout()
        version_label = QLabel("应用版本：")
        version_label.setFixedWidth(85)
        self.version_input = QLineEdit()
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_input)
        app_layout.addLayout(version_layout)

        layout.addWidget(app_group)

        # 网络设置组
        network_group = QGroupBox("网络")
        network_group.setProperty("class", "settings-group")
        network_layout = QVBoxLayout(network_group)
        network_layout.setSpacing(6)

        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("超时时间(秒)：")
        timeout_label.setFixedWidth(85)
        self.timeout_input = QLineEdit()
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout_input)
        network_layout.addLayout(timeout_layout)

        layout.addWidget(network_group)

        # 用户设置组
        user_group = QGroupBox("用户设置")
        user_group.setProperty("class", "settings-group")
        user_layout = QVBoxLayout(user_group)
        user_layout.setSpacing(6)

        # Output Path
        output_layout = QHBoxLayout()
        output_label = QLabel("输出路径：")
        output_label.setFixedWidth(85)
        self.output_input = QLineEdit()
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(browse_btn)
        user_layout.addLayout(output_layout)

        layout.addWidget(user_group)

        layout.addSpacing(12)

        # 保存按钮
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("保存设置")
        self.save_btn.setProperty("class", "primary-button")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)

        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.setProperty("class", "secondary-button")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_settings)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _on_theme_btn_click(self, theme: str) -> None:
        """主题按钮点击 - 只发射信号，不直接应用主题"""
        if self._theme_updating:
            return
        self.config_manager.set('ui.theme', theme)
        self.theme_changed.emit(theme)

    def update_theme_buttons(self, theme: str) -> None:
        """更新主题按钮状态（由外部调用）"""
        self._theme_updating = True
        try:
            if theme == 'dark':
                self.dark_theme_btn.setChecked(True)
            else:
                self.light_theme_btn.setChecked(True)
        finally:
            self._theme_updating = False

    def load_settings(self) -> None:
        """加载设置"""
        self.name_input.setText(self.config_manager.get('app.name', 'PyQt EXE 模板'))
        self.version_input.setText(self.config_manager.get('app.version', '1.0.0'))
        self.timeout_input.setText(str(self.config_manager.get('network.timeout', 30)))
        self.output_input.setText(self.config_manager.get('user_settings.output_path', './rundata/output'))

        # 加载主题设置
        theme = self.config_manager.get('ui.theme', 'dark')
        self.update_theme_buttons(theme)

    def save_settings(self) -> None:
        """保存设置"""
        try:
            self.config_manager.set('app.name', self.name_input.text())
            self.config_manager.set('app.version', self.version_input.text())
            self.config_manager.set('network.timeout', int(self.timeout_input.text()))
            self.config_manager.set('user_settings.output_path', self.output_input.text())

            QMessageBox.information(self, "成功", "设置已保存！")
        except ValueError:
            QMessageBox.warning(self, "警告", "超时时间必须是数字")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败：{str(e)}")

    def reset_settings(self) -> None:
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要恢复默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.reset_to_defaults()
            self.load_settings()
            # 重置后通知主题切换
            theme = self.config_manager.get('ui.theme', 'dark')
            self.theme_changed.emit(theme)
            QMessageBox.information(self, "成功", "已恢复默认设置！")

    def browse_output(self) -> None:
        """浏览输出目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_input.setText(folder)


# ============================================================================
# About 页面
# ============================================================================

class AboutPage(QWidget):
    """关于页面"""
    
    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setup_ui()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 页面标题
        title = QLabel("关于")
        title.setProperty("class", "page-title")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addSpacing(8)
        
        # 项目信息卡片
        info_card = CardWidget("", "")
        
        app_name = self.config_manager.get('app.name', 'PyQt EXE 模板')
        app_version = self.config_manager.get('app.version', '1.0.0')
        
        info_text = f"""
<h2>{app_name}</h2>
<p style="color: #94A3B8;">版本 {app_version}</p>
<br>
<p>一个现代化的 PyQt6 桌面应用程序模板，包含：</p>
<ul>
  <li>现代深色主题 UI，QSS 样式</li>
  <li>内置 HTTP 客户端，用于 API 测试</li>
  <li>基于 YAML 的配置管理</li>
  <li>PyInstaller 打包支持</li>
  <li>跨平台兼容</li>
</ul>
<br>
<p><b>技术栈：</b></p>
<p>Python 3.12 | PyQt6 | requests | PyYAML | PyInstaller</p>
<br>
<p><b>GitHub 仓库：</b></p>
<p style="color: #4F8CFF;"><a href="https://github.com/SoulQAQ/pyqt-exe-template" style="color: #4F8CFF;">https://github.com/SoulQAQ/pyqt-exe-template</a></p>
"""
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setOpenExternalLinks(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        
        card_layout = info_card.layout()
        card_layout.addWidget(info_label)
        
        layout.addWidget(info_card)
        
        layout.addStretch()


# ============================================================================
# 主窗口
# ============================================================================

class MainWindow(QMainWindow):
    """
    应用程序主窗口

    布局结构（自绘标题栏）：
    ┌─────────────────────────────────────────────────────────┐
    │ [标题文字..................] [🌙] [☀️] | [⚙️]  │ ← 自绘标题栏
    ├──────────┬──────────────────────────────────────────────┤
    │          │                                              │
    │  导航栏  │              内容区                          │
    │ (180px)  │                                              │
    │          │                                              │
    └──────────┴──────────────────────────────────────────────┘
    """

    # 主题切换信号
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.logger = get_logger()
        self.config_manager = get_config_manager()
        self.config = self.config_manager.load()
        self._current_theme = self.config_manager.get('ui.theme', 'dark')

        # 使用 FramelessWindowHint 实现自绘标题栏
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )

        self._init_ui()
        self._init_statusbar()
        self._load_window_state()
        self._connect_signals()

        # Windows 平台下设置窗口圆角
        if sys.platform == 'win32':
            self._setup_window_corners()

        self.logger.info("主窗口初始化完成")

    def _setup_window_corners(self) -> None:
        """设置 Windows 11 窗口圆角"""
        try:
            hwnd = int(self.winId())
            corner_preference = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(corner_preference),
                ctypes.sizeof(corner_preference)
            )
            self.logger.info("窗口圆角设置完成")
        except Exception as e:
            self.logger.warning(f"窗口圆角设置失败: {e}")

    def apply_theme(self, theme: str) -> None:
        """
        应用主题 - 统一入口，同步所有控件状态

        Args:
            theme: 主题名称，'dark' 或 'light'
        """
        self._current_theme = theme
        self.config_manager.set('ui.theme', theme)

        # 加载对应的样式表
        stylesheet = self._load_theme_stylesheet(theme)
        if stylesheet:
            QApplication.instance().setStyleSheet(stylesheet)

        # 同步更新所有主题控件
        if hasattr(self, 'title_bar'):
            self.title_bar.update_theme_state(theme)
        if hasattr(self, 'settings_page'):
            self.settings_page.update_theme_buttons(theme)

        self.theme_changed.emit(theme)
        self.logger.info(f"主题已切换: {theme}")

    def _load_theme_stylesheet(self, theme: str) -> str:
        """加载主题样式表"""
        from script.paths import resource_path

        style_file = 'styles/modern.qss' if theme == 'dark' else 'styles/light.qss'
        qss_path = resource_path(style_file)

        try:
            if qss_path.exists():
                with open(qss_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"样式文件不存在: {qss_path}")
                return ""
        except Exception as e:
            self.logger.error(f"加载样式表失败: {e}")
            return ""

    def _init_ui(self) -> None:
        """初始化用户界面"""
        # 窗口设置
        app_name = self.config_manager.get('app.name', 'PyQt EXE 模板')
        self.setWindowTitle(app_name)

        min_width = self.config_manager.get('window.minimum_width', 900)
        min_height = self.config_manager.get('window.minimum_height', 600)
        self.setMinimumSize(min_width, min_height)

        # 默认大小
        width = self.config_manager.get('window.width', 1100)
        height = self.config_manager.get('window.height', 720)
        self.resize(width, height)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局：垂直布局，顶部标题栏 + 下方内容区
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ========== 自绘标题栏 ==========
        self.title_bar = TitleBar(self)
        self.title_bar.set_title(app_name)
        root_layout.addWidget(self.title_bar)

        # ========== 主体区域：左侧导航 + 右侧内容 ==========
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        root_layout.addLayout(main_layout)

        # 左侧导航栏
        self._create_navbar(main_layout)

        # 右侧内容区
        self._create_content_area(main_layout)

    def _create_navbar(self, parent_layout: QHBoxLayout) -> None:
        """创建左侧导航栏"""
        nav_widget = QFrame()
        nav_widget.setProperty("class", "navbar")
        nav_widget.setFixedWidth(180)

        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(4)

        # 导航按钮
        self.nav_buttons = []

        self.dashboard_btn = NavButton("首页")
        self.dashboard_btn.setChecked(True)
        nav_layout.addWidget(self.dashboard_btn)
        self.nav_buttons.append(self.dashboard_btn)

        self.http_btn = NavButton("HTTP 客户端")
        nav_layout.addWidget(self.http_btn)
        self.nav_buttons.append(self.http_btn)

        self.settings_btn = NavButton("设置")
        nav_layout.addWidget(self.settings_btn)
        self.nav_buttons.append(self.settings_btn)

        self.about_btn = NavButton("关于")
        nav_layout.addWidget(self.about_btn)
        self.nav_buttons.append(self.about_btn)

        nav_layout.addStretch()

        parent_layout.addWidget(nav_widget)

    def _create_content_area(self, parent_layout: QHBoxLayout) -> None:
        """创建右侧内容区"""
        self.content_widget = QFrame()
        self.content_widget.setProperty("class", "content-area")

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)

        # 页面堆栈
        self.page_stack = QStackedWidget()

        # 创建各页面
        self.dashboard_page = DashboardPage()
        self.http_page = HttpClientPage(self.config_manager)
        self.settings_page = SettingsPage(self.config_manager)
        self.about_page = AboutPage(self.config_manager)

        self.page_stack.addWidget(self.dashboard_page)
        self.page_stack.addWidget(self.http_page)
        self.page_stack.addWidget(self.settings_page)
        self.page_stack.addWidget(self.about_page)

        content_layout.addWidget(self.page_stack)

        parent_layout.addWidget(self.content_widget)

    def _init_statusbar(self) -> None:
        """初始化状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_bar.showMessage("就绪")

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(150)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _load_window_state(self) -> None:
        """加载窗口状态"""
        if self.config_manager.get('window.remember_geometry', True):
            geometry = self.config_manager.get('window.geometry', '')
            if geometry:
                try:
                    import base64
                    self.restoreGeometry(bytes.fromhex(geometry))
                except Exception:
                    pass

    def _save_window_state(self) -> None:
        """保存窗口状态"""
        if self.config_manager.get('window.remember_geometry', True):
            geometry = self.saveGeometry().toHex().data().decode()
            self.config_manager.set('window.geometry', geometry)

    def _connect_signals(self) -> None:
        """连接信号"""
        # 导航按钮
        self.dashboard_btn.clicked.connect(lambda: self._switch_page(0))
        self.http_btn.clicked.connect(lambda: self._switch_page(1))
        self.settings_btn.clicked.connect(lambda: self._switch_page(2))
        self.about_btn.clicked.connect(lambda: self._switch_page(3))

        # Dashboard 快捷按钮
        self.dashboard_page.open_config_btn.clicked.connect(lambda: open_folder(CONFIG_DIR))
        self.dashboard_page.open_output_btn.clicked.connect(lambda: open_folder(OUTPUT_DIR))
        self.dashboard_page.test_http_btn.clicked.connect(lambda: self._switch_page(1))

        # 设置页面主题切换
        self.settings_page.theme_changed.connect(self.apply_theme)

        # 标题栏按钮信号
        self.title_bar.theme_clicked.connect(self.apply_theme)
        self.title_bar.settings_clicked.connect(lambda: self._switch_page(2))

    def _switch_page(self, index: int) -> None:
        """切换页面"""
        self.page_stack.setCurrentIndex(index)

        # 更新导航按钮状态
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # 更新状态栏
        page_names = ["首页", "HTTP 客户端", "设置", "关于"]
        self.status_bar.showMessage(f"{page_names[index]}")

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        self._save_window_state()
        self.logger.info("应用程序关闭")
        event.accept()
