#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyQt 主窗口模块
提供应用程序的主界面，包含现代化深色主题 UI
"""

import json
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QFrame,
    QStackedWidget, QStatusBar, QMenuBar, QToolBar, QMessageBox,
    QProgressBar, QFileDialog, QScrollArea, QSizePolicy, QGroupBox
)

from script.config_manager import get_config_manager, ConfigManager
from script.network import HttpClient, HttpResponse
from script.paths import APP_DIR, CONFIG_DIR, OUTPUT_DIR, INPUT_DIR
from script.utils import open_folder, format_json, safe_json_loads
from script.logger import get_logger


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
        self.setFixedHeight(45)


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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
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
        layout.setSpacing(20)
        
        # 欢迎标题
        welcome_label = QLabel("Welcome to PyQt EXE Template")
        welcome_label.setProperty("class", "page-title")
        welcome_label.setFont(QFont("Microsoft YaHei UI", 24, QFont.Weight.Bold))
        layout.addWidget(welcome_label)
        
        subtitle = QLabel("A modern PyQt6 desktop application template with HTTP client support")
        subtitle.setProperty("class", "page-subtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # 功能卡片区域
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        card1 = CardWidget("PyQt6 UI", "Modern dark theme with QSS styling")
        cards_layout.addWidget(card1)
        
        card2 = CardWidget("HTTP Client", "Built-in HTTP request testing tool")
        cards_layout.addWidget(card2)
        
        card3 = CardWidget("Config Manager", "YAML-based configuration system")
        cards_layout.addWidget(card3)
        
        card4 = CardWidget("PyInstaller", "Easy Windows EXE packaging")
        cards_layout.addWidget(card4)
        
        layout.addLayout(cards_layout)
        
        layout.addSpacing(20)
        
        # 快捷操作区域
        actions_label = QLabel("Quick Actions")
        actions_label.setProperty("class", "section-title")
        actions_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        layout.addWidget(actions_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        self.open_config_btn = QPushButton("Open Config Folder")
        self.open_config_btn.setProperty("class", "action-button")
        self.open_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.open_config_btn)
        
        self.open_output_btn = QPushButton("Open Output Folder")
        self.open_output_btn.setProperty("class", "action-button")
        self.open_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.open_output_btn)
        
        self.test_http_btn = QPushButton("Test HTTP Request")
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
        layout.setSpacing(15)
        
        # 页面标题
        title = QLabel("HTTP Client")
        title.setProperty("class", "page-title")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        desc = QLabel("Test HTTP requests with custom headers and body")
        desc.setProperty("class", "page-subtitle")
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # URL 和 Method 行
        url_layout = QHBoxLayout()
        
        method_label = QLabel("Method:")
        method_label.setFixedWidth(60)
        url_layout.addWidget(method_label)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(['GET', 'POST', 'PUT', 'DELETE'])
        self.method_combo.setFixedWidth(100)
        url_layout.addWidget(self.method_combo)
        
        url_label = QLabel("URL:")
        url_label.setFixedWidth(40)
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL...")
        default_url = self.config_manager.get('network.default_url', 'https://httpbin.org/get')
        self.url_input.setText(default_url)
        url_layout.addWidget(self.url_input)
        
        layout.addLayout(url_layout)
        
        # Headers 输入
        headers_label = QLabel("Headers (JSON):")
        layout.addWidget(headers_label)
        
        self.headers_input = QTextEdit()
        self.headers_input.setPlaceholderText('{\n  "Content-Type": "application/json"\n}')
        self.headers_input.setMaximumHeight(80)
        self.headers_input.setFont(QFont("Consolas", 10))
        layout.addWidget(self.headers_input)
        
        # Body 输入
        self.body_label = QLabel("Body (JSON):")
        layout.addWidget(self.body_label)
        
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText('{\n  "key": "value"\n}')
        self.body_input.setMaximumHeight(100)
        self.body_input.setFont(QFont("Consolas", 10))
        layout.addWidget(self.body_input)
        
        # 发送按钮
        btn_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("Send Request")
        self.send_btn.setProperty("class", "primary-button")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_request)
        btn_layout.addWidget(self.send_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("class", "secondary-button")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_response)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 响应区域
        response_label = QLabel("Response:")
        layout.addWidget(response_label)
        
        # 状态信息行
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Status: -")
        self.status_label.setProperty("class", "status-label")
        status_layout.addWidget(self.status_label)
        
        self.time_label = QLabel("Time: -")
        self.time_label.setProperty("class", "time-label")
        status_layout.addWidget(self.time_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 响应内容
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setFont(QFont("Consolas", 10))
        self.response_output.setPlaceholderText("Response will appear here...")
        layout.addWidget(self.response_output)
    
    def send_request(self) -> None:
        """发送 HTTP 请求"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return
        
        method = self.method_combo.currentText()
        headers_text = self.headers_input.toPlainText().strip()
        body_text = self.body_input.toPlainText().strip()
        
        headers = {}
        if headers_text:
            headers = safe_json_loads(headers_text, {})
            if headers is None:
                QMessageBox.warning(self, "Warning", "Invalid JSON in Headers")
                return
        
        timeout = self.config_manager.get('network.timeout', 30)
        
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Sending...")
        self.status_label.setText("Status: Sending...")
        
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
        self.send_btn.setText("Send Request")
        
        status_color = "#22C55E" if response.success else "#EF4444"
        self.status_label.setText(f"Status: {response.status_code}")
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        
        self.time_label.setText(f"Time: {response.elapsed_ms:.0f} ms")
        
        if response.data is not None:
            formatted = format_json(response.data)
            self.response_output.setPlainText(formatted)
        else:
            self.response_output.setPlainText(response.text or "(Empty response)")
        
        if not response.success:
            self.response_output.append(f"\n\n--- Error ---\n{response.message}")
    
    def on_request_error(self, error: str) -> None:
        """请求错误回调"""
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send Request")
        
        self.status_label.setText("Status: Error")
        self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.time_label.setText("Time: -")
        
        self.response_output.setPlainText(f"Request failed:\n{error}")
    
    def clear_response(self) -> None:
        """清空响应"""
        self.response_output.clear()
        self.status_label.setText("Status: -")
        self.status_label.setStyleSheet("")
        self.time_label.setText("Time: -")


# ============================================================================
# Settings 页面
# ============================================================================

class SettingsPage(QWidget):
    """设置页面"""
    
    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 页面标题
        title = QLabel("Settings")
        title.setProperty("class", "page-title")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        desc = QLabel("Configure application settings")
        desc.setProperty("class", "page-subtitle")
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # 应用设置组
        app_group = QGroupBox("Application")
        app_group.setProperty("class", "settings-group")
        app_layout = QVBoxLayout(app_group)
        
        # App Name
        name_layout = QHBoxLayout()
        name_label = QLabel("App Name:")
        name_label.setFixedWidth(120)
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        app_layout.addLayout(name_layout)
        
        # App Version
        version_layout = QHBoxLayout()
        version_label = QLabel("App Version:")
        version_label.setFixedWidth(120)
        self.version_input = QLineEdit()
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_input)
        app_layout.addLayout(version_layout)
        
        layout.addWidget(app_group)
        
        # 网络设置组
        network_group = QGroupBox("Network")
        network_group.setProperty("class", "settings-group")
        network_layout = QVBoxLayout(network_group)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Timeout (s):")
        timeout_label.setFixedWidth(120)
        self.timeout_input = QLineEdit()
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout_input)
        network_layout.addLayout(timeout_layout)
        
        layout.addWidget(network_group)
        
        # 用户设置组
        user_group = QGroupBox("User Settings")
        user_group.setProperty("class", "settings-group")
        user_layout = QVBoxLayout(user_group)
        
        # Output Path
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Path:")
        output_label.setFixedWidth(120)
        self.output_input = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(browse_btn)
        user_layout.addLayout(output_layout)
        
        layout.addWidget(user_group)
        
        layout.addSpacing(20)
        
        # 保存按钮
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setProperty("class", "primary-button")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setProperty("class", "secondary-button")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_settings)
        btn_layout.addWidget(self.reset_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def load_settings(self) -> None:
        """加载设置"""
        self.name_input.setText(self.config_manager.get('app.name', 'PyQt EXE Template'))
        self.version_input.setText(self.config_manager.get('app.version', '1.0.0'))
        self.timeout_input.setText(str(self.config_manager.get('network.timeout', 30)))
        self.output_input.setText(self.config_manager.get('user_settings.output_path', './rundata/output'))
    
    def save_settings(self) -> None:
        """保存设置"""
        try:
            self.config_manager.set('app.name', self.name_input.text())
            self.config_manager.set('app.version', self.version_input.text())
            self.config_manager.set('network.timeout', int(self.timeout_input.text()))
            self.config_manager.set('user_settings.output_path', self.output_input.text())
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid timeout value. Please enter a number.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def reset_settings(self) -> None:
        """重置设置"""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(self, "Success", "Settings reset to defaults!")
    
    def browse_output(self) -> None:
        """浏览输出目录"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
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
        layout.setSpacing(20)
        
        # 页面标题
        title = QLabel("About")
        title.setProperty("class", "page-title")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # 项目信息卡片
        info_card = CardWidget("", "")
        
        app_name = self.config_manager.get('app.name', 'PyQt EXE Template')
        app_version = self.config_manager.get('app.version', '1.0.0')
        
        info_text = f"""
<h2>{app_name}</h2>
<p style="color: #94A3B8;">Version {app_version}</p>
<br>
<p>A modern PyQt6 desktop application template with:</p>
<ul>
  <li>Modern dark theme UI with QSS styling</li>
  <li>Built-in HTTP client for API testing</li>
  <li>YAML-based configuration management</li>
  <li>PyInstaller packaging support</li>
  <li>Cross-platform compatibility</li>
</ul>
<br>
<p><b>Technology Stack:</b></p>
<p>Python 3.12 | PyQt6 | requests | PyYAML | PyInstaller</p>
<br>
<p><b>GitHub Repository:</b></p>
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
    """应用程序主窗口"""

    def __init__(self):
        super().__init__()
        
        self.logger = get_logger()
        self.config_manager = get_config_manager()
        self.config = self.config_manager.load()
        
        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._load_window_state()
        self._connect_signals()
        
        self.logger.info("MainWindow initialized")

    def _init_ui(self) -> None:
        """初始化用户界面"""
        # 窗口设置
        app_name = self.config_manager.get('app.name', 'PyQt EXE Template')
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
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧导航栏
        self._create_navbar(main_layout)
        
        # 右侧内容区
        self._create_content_area(main_layout)

    def _create_navbar(self, parent_layout: QHBoxLayout) -> None:
        """创建左侧导航栏"""
        nav_widget = QFrame()
        nav_widget.setProperty("class", "navbar")
        nav_widget.setFixedWidth(220)
        
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(5)
        
        # Logo/标题
        logo_label = QLabel("PyQt Template")
        logo_label.setProperty("class", "nav-logo")
        logo_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(logo_label)
        
        nav_layout.addSpacing(30)
        
        # 导航按钮
        self.nav_buttons = []
        
        self.dashboard_btn = NavButton("Dashboard", "H")
        self.dashboard_btn.setChecked(True)
        nav_layout.addWidget(self.dashboard_btn)
        self.nav_buttons.append(self.dashboard_btn)
        
        self.http_btn = NavButton("HTTP Client", "G")
        nav_layout.addWidget(self.http_btn)
        self.nav_buttons.append(self.http_btn)
        
        self.settings_btn = NavButton("Settings", "S")
        nav_layout.addWidget(self.settings_btn)
        self.nav_buttons.append(self.settings_btn)
        
        self.about_btn = NavButton("About", "i")
        nav_layout.addWidget(self.about_btn)
        self.nav_buttons.append(self.about_btn)
        
        nav_layout.addStretch()
        
        parent_layout.addWidget(nav_widget)

    def _create_content_area(self, parent_layout: QHBoxLayout) -> None:
        """创建右侧内容区"""
        content_widget = QFrame()
        content_widget.setProperty("class", "content-area")
        
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
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
        
        parent_layout.addWidget(content_widget)

    def _init_menu(self) -> None:
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # File 菜单
        file_menu = menubar.addMenu("File")
        
        open_config_action = QAction("Open Config Folder", self)
        open_config_action.triggered.connect(lambda: open_folder(CONFIG_DIR))
        file_menu.addAction(open_config_action)
        
        open_output_action = QAction("Open Output Folder", self)
        open_output_action.triggered.connect(lambda: open_folder(OUTPUT_DIR))
        file_menu.addAction(open_output_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools 菜单
        tools_menu = menubar.addMenu("Tools")
        
        test_http_action = QAction("Test HTTP Request", self)
        test_http_action.triggered.connect(lambda: self._switch_page(1))
        tools_menu.addAction(test_http_action)
        
        # Help 菜单
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: self._switch_page(3))
        help_menu.addAction(about_action)

    def _init_toolbar(self) -> None:
        """初始化工具栏"""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        
        home_action = QAction("Home", self)
        home_action.triggered.connect(lambda: self._switch_page(0))
        toolbar.addAction(home_action)
        
        http_action = QAction("HTTP", self)
        http_action.triggered.connect(lambda: self._switch_page(1))
        toolbar.addAction(http_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(lambda: self._switch_page(2))
        toolbar.addAction(settings_action)

    def _init_statusbar(self) -> None:
        """初始化状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_bar.showMessage("Ready")
        
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
                    self.restoreGeometry(base64.b64decode(geometry))
                except Exception:
                    pass

    def _save_window_state(self) -> None:
        """保存窗口状态"""
        if self.config_manager.get('window.remember_geometry', True):
            import base64
            geometry = base64.b64encode(self.saveGeometry()).decode('utf-8')
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

    def _switch_page(self, index: int) -> None:
        """切换页面"""
        self.page_stack.setCurrentIndex(index)
        
        # 更新导航按钮状态
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        
        # 更新状态栏
        page_names = ["Dashboard", "HTTP Client", "Settings", "About"]
        self.status_bar.showMessage(f"{page_names[index]}")

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        self._save_window_state()
        self.logger.info("Application closing")
        event.accept()
