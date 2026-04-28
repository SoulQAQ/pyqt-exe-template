#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyQt EXE Template - 程序入口
主程序启动文件
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from script.paths import APP_DIR, RESOURCE_DIR, resource_path, ensure_dir, LOGS_DIR
from script.logger import init_logging, get_logger
from script.config_manager import get_config_manager


def load_stylesheet() -> str:
    """
    加载 QSS 样式表
    
    Returns:
        str: 样式表内容
    """
    qss_path = resource_path('styles/modern.qss')
    
    try:
        if qss_path.exists():
            with open(qss_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"Warning: QSS file not found: {qss_path}")
            return ""
    except Exception as e:
        print(f"Error loading QSS: {e}")
        return ""


def main() -> int:
    """
    应用程序主入口
    
    Returns:
        int: 退出码
    """
    # 确保日志目录存在
    ensure_dir(LOGS_DIR)
    
    # 初始化日志系统
    logger = init_logging()
    logger.info("=" * 50)
    logger.info("PyQt EXE Template starting...")
    logger.info(f"Application directory: {APP_DIR}")
    logger.info(f"Resource directory: {RESOURCE_DIR}")
    
    try:
        # 创建 QApplication 实例
        app = QApplication(sys.argv)
        
        # 设置应用程序信息
        app.setApplicationName("PyQt EXE Template")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("SoulQAQ")
        
        # 设置默认字体
        font = QFont("Microsoft YaHei UI", 10)
        app.setFont(font)
        
        # 加载配置
        config_manager = get_config_manager()
        config = config_manager.load()
        logger.info("Configuration loaded")
        
        # 加载样式表
        stylesheet = load_stylesheet()
        if stylesheet:
            app.setStyleSheet(stylesheet)
            logger.info("Stylesheet loaded successfully")
        else:
            logger.warning("No stylesheet loaded, using default style")
        
        # 导入并创建主窗口（延迟导入以加快启动）
        from script.gui import MainWindow
        
        window = MainWindow()
        window.show()
        
        logger.info("Application started successfully")
        
        # 启动事件循环
        exit_code = app.exec()
        
        logger.info(f"Application exiting with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.exception(f"Application error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
