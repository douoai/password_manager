import sys
import json
import os
import qrcode
from PIL import Image
import socket
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QListWidget, QLineEdit, QPushButton, 
                            QLabel, QMessageBox, QDialog, QFormLayout, QTextEdit,
                            QGroupBox, QComboBox, QStyleFactory, QFrame, QInputDialog,
                            QListWidgetItem, QStackedWidget, QSpinBox)
from PyQt6.QtCore import Qt, QSize, QBuffer, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QShortcut, QKeySequence
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.Util.Padding import pad, unpad
import base64
from datetime import datetime
import subprocess

print("开始初始化...")

def check_dependencies():
    try:
        import PIL
        print("PIL版本:", PIL.__version__)
    except Exception as e:
        print(f"PIL导入失败: {str(e)}")
        sys.exit(1)
    
    try:
        import qrcode
        print("qrcode导入成功")
    except Exception as e:
        print(f"qrcode导入失败: {str(e)}")
        sys.exit(1)

check_dependencies()

class PasswordDialog(QDialog):
    def __init__(self, parent=None, password_data=None):
        super().__init__(parent)
        self.password_data = password_data
        self.is_password_visible = False  # 添加密码显示状态标志
        self.setup_ui()
        self.setup_style()
        
    def setup_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: "Microsoft YaHei", "微软雅黑";
            }
            QLabel {
                font-size: 13px;
                color: #2c3e50;
            }
            QLineEdit, QTextEdit {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 13px;
                selection-background-color: #a8d8ff;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #7eb9ff;
                background-color: #ffffff;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #7eb9ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                min-width: 90px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5ca3ff;
            }
            QPushButton:pressed {
                background-color: #4b8fe0;
            }
            QPushButton#showPasswordBtn {
                background-color: #f0f0f0;
                color: #2c3e50;
            }
            QPushButton#showPasswordBtn:hover {
                background-color: #e0e0e0;
            }
            QPushButton#showPasswordBtn:checked {
                background-color: #7eb9ff;
                color: white;
            }
        """)
        
    def setup_ui(self):
        self.setWindowTitle("密码详情")
        self.setMinimumWidth(450)
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 设置字体
        font = QFont("Microsoft YaHei", 10)
        self.setFont(font)
        
        self.title_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://")
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(120)
        
        # 添加密码显示切换按钮
        password_layout = QHBoxLayout()
        password_layout.setSpacing(8)
        password_layout.addWidget(self.password_edit)
        self.show_password_btn = QPushButton("显示")  # 改为实例变量
        self.show_password_btn.setObjectName("showPasswordBtn")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)  # 使用新的方法
        password_layout.addWidget(self.show_password_btn)
        
        # 设置标签样式
        title_label = QLabel("标题：")
        username_label = QLabel("用户名：")
        password_label = QLabel("密码：")
        url_label = QLabel("登录地址：")
        notes_label = QLabel("备注：")
        
        for label in [title_label, username_label, password_label, url_label, notes_label]:
            label.setStyleSheet("font-weight: 500;")
        
        layout.addRow(title_label, self.title_edit)
        layout.addRow(username_label, self.username_edit)
        layout.addRow(password_label, password_layout)
        layout.addRow(url_label, self.url_edit)
        layout.addRow(notes_label, self.notes_edit)
        
        if self.password_data:
            self.title_edit.setText(self.password_data.get('title', ''))
            self.username_edit.setText(self.password_data.get('username', ''))
            self.password_edit.setText(self.password_data.get('password', ''))
            self.url_edit.setText(self.password_data.get('url', ''))
            self.notes_edit.setText(self.password_data.get('notes', ''))
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.is_password_visible = False
            self.show_password_btn.setChecked(False)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
        
        self.setLayout(layout)

    def toggle_password_visibility(self):
        """切换密码显示/隐藏状态"""
        self.is_password_visible = not self.is_password_visible
        if self.is_password_visible:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("隐藏")
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("显示")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent  # 保存父窗口引用
        self.setFixedSize(800, 600)  # 固定窗口大小
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)  # 移除帮助按钮
        self.setup_ui()
        self.setup_style()
        self.load_shortcuts()  # 加载快捷键设置
        
    def setup_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: "Microsoft YaHei", "微软雅黑";
            }
            QWidget#leftPanel {
                background-color: #f8f9fa;
                border-right: 1px solid #e0e0e0;
            }
            QWidget#rightPanel {
                background-color: #ffffff;
            }
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px 15px;
                color: #2c3e50;
                border-radius: 4px;
                margin: 2px 8px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                font-weight: 500;
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                min-width: 100px;
                font-weight: 500;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                opacity: 0.8;
            }
            QPushButton#saveBtn {
                background-color: #2196f3;
                color: white;
            }
            QPushButton#saveBtn:hover {
                background-color: #1976d2;
            }
            QPushButton#cancelBtn {
                background-color: #9E9E9E;
                color: white;
            }
            QPushButton#cancelBtn:hover {
                background-color: #757575;
            }
            QPushButton#changePasswordBtn {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton#changePasswordBtn:hover {
                background-color: #43A047;
            }
            QPushButton#exportBtn {
                background-color: #FF9800;
                color: white;
            }
            QPushButton#exportBtn:hover {
                background-color: #F57C00;
            }
            QPushButton#importBtn {
                background-color: #9C27B0;
                color: white;
            }
            QPushButton#importBtn:hover {
                background-color: #7B1FA2;
            }
            QPushButton#resetBtn {
                background-color: #607D8B;
                color: white;
            }
            QPushButton#resetBtn:hover {
                background-color: #546E7A;
            }
            QPushButton#saveShortcutsBtn {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton#saveShortcutsBtn:hover {
                background-color: #43A047;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #7eb9ff;
                background-color: #ffffff;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: 500;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdbdbd;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9e9e9e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
    def setup_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumWidth(600)
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧列表
        left_panel = QWidget()
        left_panel.setFixedWidth(200)
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout()
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 设置列表
        self.settings_list = QListWidget()
        self.settings_list.addItems(["主密码设置", "数据迁移", "快捷键设置"])
        self.settings_list.currentRowChanged.connect(self.show_settings_page)
        left_layout.addWidget(self.settings_list)
        
        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel)
        
        # 右侧内容
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(30, 30, 30, 30)
        right_panel.setLayout(right_layout)
        
        # 创建堆叠窗口
        self.settings_stack = QStackedWidget()
        
        # 主密码设置页面
        password_page = QWidget()
        password_layout = QVBoxLayout()
        
        # 当前密码
        current_password_layout = QHBoxLayout()
        current_password_label = QLabel("当前主密码：")
        self.current_password_edit = QLineEdit()
        self.current_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        current_password_layout.addWidget(current_password_label)
        current_password_layout.addWidget(self.current_password_edit)
        password_layout.addLayout(current_password_layout)
        
        # 新密码
        new_password_layout = QHBoxLayout()
        new_password_label = QLabel("新主密码：")
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        new_password_layout.addWidget(new_password_label)
        new_password_layout.addWidget(self.new_password_edit)
        password_layout.addLayout(new_password_layout)
        
        # 确认新密码
        confirm_password_layout = QHBoxLayout()
        confirm_password_label = QLabel("确认新密码：")
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_password_layout.addWidget(confirm_password_label)
        confirm_password_layout.addWidget(self.confirm_password_edit)
        password_layout.addLayout(confirm_password_layout)
        
        # 密码要求提示
        password_requirements = QLabel(
            "密码要求：\n" +
            "• 至少8个字符\n" +
            "• 包含大写字母\n" +
            "• 包含小写字母\n" +
            "• 包含数字\n" +
            "• 包含特殊字符（如：!@#$%^&*等）"
        )
        password_requirements.setStyleSheet("color: #666; font-size: 12px;")
        password_layout.addWidget(password_requirements)
        
        # 修改密码按钮
        change_password_btn = QPushButton("修改主密码")
        change_password_btn.setObjectName("changePasswordBtn")
        change_password_btn.clicked.connect(self.change_master_password)
        password_layout.addWidget(change_password_btn)
        
        password_layout.addStretch()
        password_page.setLayout(password_layout)
        
        # 数据迁移页面
        migration_page = QWidget()
        migration_layout = QVBoxLayout()
        
        # 导出数据按钮
        export_btn = QPushButton("导出数据")
        export_btn.setObjectName("exportBtn")
        export_btn.clicked.connect(self.export_data)
        migration_layout.addWidget(export_btn)
        
        # 导入数据按钮
        import_btn = QPushButton("导入数据")
        import_btn.setObjectName("importBtn")
        import_btn.clicked.connect(self.import_data)
        migration_layout.addWidget(import_btn)
        
        migration_layout.addStretch()
        migration_page.setLayout(migration_layout)
        
        # 快捷键设置页面
        shortcuts_page = QWidget()
        shortcuts_layout = QVBoxLayout()
        
        # 全局快捷键组
        global_group = QGroupBox("全局快捷键")
        global_layout = QFormLayout()
        
        # 全局快速查找
        self.global_search_edit = QLineEdit()
        self.global_search_edit.setReadOnly(True)
        self.global_search_edit.setPlaceholderText("点击设置快捷键")
        self.global_search_edit.mousePressEvent = lambda e: self.start_shortcut_capture(self.global_search_edit, "global_search")
        global_layout.addRow("快速查找:", self.global_search_edit)
        
        # 快速锁定
        self.global_lock_edit = QLineEdit()
        self.global_lock_edit.setReadOnly(True)
        self.global_lock_edit.setPlaceholderText("点击设置快捷键")
        self.global_lock_edit.mousePressEvent = lambda e: self.start_shortcut_capture(self.global_lock_edit, "global_lock")
        global_layout.addRow("快速锁定:", self.global_lock_edit)
        
        # 打开主界面
        self.global_show_edit = QLineEdit()
        self.global_show_edit.setReadOnly(True)
        self.global_show_edit.setPlaceholderText("点击设置快捷键")
        self.global_show_edit.mousePressEvent = lambda e: self.start_shortcut_capture(self.global_show_edit, "global_show")
        global_layout.addRow("打开主界面:", self.global_show_edit)
        
        # 隐藏主界面
        self.global_hide_edit = QLineEdit()
        self.global_hide_edit.setReadOnly(True)
        self.global_hide_edit.setPlaceholderText("点击设置快捷键")
        self.global_hide_edit.mousePressEvent = lambda e: self.start_shortcut_capture(self.global_hide_edit, "global_hide")
        global_layout.addRow("隐藏主界面:", self.global_hide_edit)
        
        global_group.setLayout(global_layout)
        shortcuts_layout.addWidget(global_group)
        
        # 软件内快捷键组
        app_group = QGroupBox("软件内快捷键")
        app_layout = QFormLayout()
        
        # 快速查找
        self.app_search_edit = QLineEdit()
        self.app_search_edit.setReadOnly(True)
        self.app_search_edit.setPlaceholderText("点击设置快捷键")
        self.app_search_edit.mousePressEvent = lambda e: self.start_shortcut_capture(self.app_search_edit, "app_search")
        app_layout.addRow("快速查找:", self.app_search_edit)
        
        # 快速添加
        self.app_add_edit = QLineEdit()
        self.app_add_edit.setReadOnly(True)
        self.app_add_edit.setPlaceholderText("点击设置快捷键")
        self.app_add_edit.mousePressEvent = lambda e: self.start_shortcut_capture(self.app_add_edit, "app_add")
        app_layout.addRow("快速添加:", self.app_add_edit)
        
        app_group.setLayout(app_layout)
        shortcuts_layout.addWidget(app_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        # 恢复默认按钮
        reset_btn = QPushButton("恢复默认")
        reset_btn.setObjectName("resetBtn")
        reset_btn.clicked.connect(self.reset_shortcuts)
        button_layout.addWidget(reset_btn)
        
        # 保存按钮
        save_shortcuts_btn = QPushButton("保存")
        save_shortcuts_btn.setObjectName("saveShortcutsBtn")
        save_shortcuts_btn.clicked.connect(self.save_shortcuts)
        button_layout.addWidget(save_shortcuts_btn)
        
        shortcuts_layout.addLayout(button_layout)
        shortcuts_page.setLayout(shortcuts_layout)
        
        # 添加页面到堆叠窗口
        self.settings_stack.addWidget(password_page)
        self.settings_stack.addWidget(migration_page)
        self.settings_stack.addWidget(shortcuts_page)
        
        right_layout.addWidget(self.settings_stack)
        layout.addWidget(right_panel)
        
        # 底部按钮
        self.bottom_button_layout = QHBoxLayout()
        self.bottom_button_layout.setContentsMargins(30, 0, 30, 30)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self.accept)
        self.bottom_button_layout.addWidget(self.save_btn)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        self.bottom_button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(self.bottom_button_layout)
        self.setLayout(layout)
        
        # 默认选中第一项
        self.settings_list.setCurrentRow(0)
        
        # 初始化快捷键捕获状态
        self.capturing_shortcut = False
        self.current_shortcut_key = None
        self.current_shortcut_edit = None
        
    def show_settings_page(self, index):
        """切换设置页面"""
        self.settings_stack.setCurrentIndex(index)
        
        # 隐藏所有页面的底部按钮
        self.save_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
    
    def start_shortcut_capture(self, edit, shortcut_key):
        """开始捕获快捷键"""
        self.capturing_shortcut = True
        self.current_shortcut_key = shortcut_key
        self.current_shortcut_edit = edit
        edit.setText("请按下快捷键...")
        edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #2196f3;
                border-radius: 6px;
                background-color: #e3f2fd;
                font-size: 13px;
            }
        """)
        
    def keyPressEvent(self, event):
        """处理按键事件"""
        if self.capturing_shortcut:
            # 获取按键组合
            modifiers = []
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                modifiers.append("Ctrl")
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                modifiers.append("Alt")
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                modifiers.append("Shift")
            if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
                modifiers.append("Win")
                
            key = event.key()
            if key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z:
                key_text = chr(key)
            elif key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F12:
                key_text = f"F{key - Qt.Key.Key_F1 + 1}"
            else:
                key_text = QKeySequence(key).toString()
                
            if key_text:
                shortcut = "+".join(modifiers + [key_text])
                self.current_shortcut_edit.setText(shortcut)
                self.current_shortcut_edit.setStyleSheet("")
                self.capturing_shortcut = False
                self.current_shortcut_key = None
                self.current_shortcut_edit = None
                # 立即保存快捷键设置
                self.save_shortcuts()
        else:
            super().keyPressEvent(event)
            
    def load_shortcuts(self):
        """加载快捷键设置"""
        try:
            if os.path.exists('shortcuts.json'):
                with open('shortcuts.json', 'r', encoding='utf-8') as f:
                    shortcuts = json.load(f)
            else:
                shortcuts = self.get_default_shortcuts()
                
            # 设置全局快捷键
            self.global_search_edit.setText(shortcuts.get('global_search', 'Ctrl+Alt+F'))
            self.global_lock_edit.setText(shortcuts.get('global_lock', 'Ctrl+Alt+L'))
            self.global_show_edit.setText(shortcuts.get('global_show', 'Ctrl+Alt+S'))
            self.global_hide_edit.setText(shortcuts.get('global_hide', 'Ctrl+Alt+H'))
            
            # 设置软件内快捷键
            self.app_search_edit.setText(shortcuts.get('app_search', 'Ctrl+F'))
            self.app_add_edit.setText(shortcuts.get('app_add', 'Ctrl+N'))
            
        except Exception as e:
            self.parent.show_messagebox('warn', "错误", f"加载快捷键设置失败：{str(e)}")
            self.reset_shortcuts()
            
    def save_shortcuts(self):
        """保存快捷键设置"""
        try:
            shortcuts = {
                'global_search': self.global_search_edit.text(),
                'global_lock': self.global_lock_edit.text(),
                'global_show': self.global_show_edit.text(),
                'global_hide': self.global_hide_edit.text(),
                'app_search': self.app_search_edit.text(),
                'app_add': self.app_add_edit.text()
            }
            
            with open('shortcuts.json', 'w', encoding='utf-8') as f:
                json.dump(shortcuts, f, ensure_ascii=False, indent=2)
                
            self.parent.show_messagebox('info', "成功", "快捷键设置已保存")
            
        except Exception as e:
            self.parent.show_messagebox('warn', "错误", f"保存快捷键设置失败：{str(e)}")
            
    def reset_shortcuts(self):
        """重置快捷键为默认值"""
        shortcuts = self.get_default_shortcuts()
        
        # 设置全局快捷键
        self.global_search_edit.setText(shortcuts['global_search'])
        self.global_lock_edit.setText(shortcuts['global_lock'])
        self.global_show_edit.setText(shortcuts['global_show'])
        self.global_hide_edit.setText(shortcuts['global_hide'])
        
        # 设置软件内快捷键
        self.app_search_edit.setText(shortcuts['app_search'])
        self.app_add_edit.setText(shortcuts['app_add'])
        
    def get_default_shortcuts(self):
        """获取默认快捷键设置"""
        return {
            'global_search': 'Ctrl+Alt+F',
            'global_lock': 'Ctrl+Alt+L',
            'global_show': 'Ctrl+Alt+S',
            'global_hide': 'Ctrl+Alt+H',
            'app_search': 'Ctrl+F',
            'app_add': 'Ctrl+N'
        }
    
    def export_data(self):
        """导出数据"""
        try:
            # 验证当前密码
            current_password = self.current_password_edit.text()
            if not current_password:
                self.parent.show_messagebox('warn', "错误", "请输入当前主密码")
                return
                
            key = PBKDF2(current_password.encode(), self.parent.salt, dkLen=32)
            with open('master.key', 'rb') as f:
                stored_key = f.read()
            if key != stored_key:
                self.parent.show_messagebox('warn', "错误", "当前主密码不正确")
                return
            
            # 选择保存位置
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出数据",
                "password_manager_backup.json",
                "JSON Files (*.json)"
            )
            
            if file_path:
                # 导出数据
                with open(self.parent.data_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                
                # 保存加密数据和盐值
                export_data = {
                    'encrypted_data': encrypted_data,
                    'salt': base64.b64encode(self.parent.salt).decode('utf-8')
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                self.parent.show_messagebox('info', "成功", "数据导出成功！")
                
        except Exception as e:
            self.parent.show_messagebox('crit', "错误", f"导出数据时发生错误：{str(e)}")
    
    def import_data(self):
        """导入数据"""
        try:
            # 选择导入文件
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "导入数据",
                "",
                "JSON Files (*.json)"
            )
            
            if not file_path:
                return
                
            # 读取导入数据
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(import_data, dict) or 'encrypted_data' not in import_data or 'salt' not in import_data:
                self.parent.show_messagebox('warn', "错误", "无效的数据文件格式")
                return
            
            # 验证当前密码
            current_password = self.current_password_edit.text()
            if not current_password:
                self.parent.show_messagebox('warn', "错误", "请输入当前主密码")
                return
            
            # 尝试解密数据
            try:
                salt = base64.b64decode(import_data['salt'])
                key = PBKDF2(current_password.encode(), salt, dkLen=32)
                cipher = AES.new(key, AES.MODE_CBC, base64.b64decode(import_data['encrypted_data']['iv']))
                pt = unpad(cipher.decrypt(base64.b64decode(import_data['encrypted_data']['ciphertext'])), AES.block_size)
                json.loads(pt.decode('utf-8'))  # 验证JSON格式
            except Exception as e:
                self.parent.show_messagebox('warn', "错误", "密码不正确或数据已损坏")
                return
            
            # 确认导入
            reply = self.parent.show_messagebox('yesno', "确认导入",
                "导入数据将覆盖当前所有密码数据，是否继续？\n\n" +
                "注意：请确保已备份当前数据。"
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 更新盐值
                self.parent.salt = salt
                with open('salt.bin', 'wb') as f:
                    f.write(salt)
                
                # 更新主密码
                self.parent.master_password = current_password
                self.parent.save_master_key()
                
                # 保存加密数据
                with open(self.parent.data_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(import_data['encrypted_data']))
                
                # 重新加载数据
                self.parent.load_data()
                
                self.parent.show_messagebox('info', "成功", "数据导入成功！")
                
        except Exception as e:
            self.parent.show_messagebox('crit', "错误", f"导入数据时发生错误：{str(e)}")

    def change_master_password(self):
        """修改主密码"""
        current_password = self.current_password_edit.text()
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        # 验证当前密码
        if not current_password:
            self.parent.show_messagebox('warn', "错误", "请输入当前主密码")
            return
            
        # 验证新密码
        if not new_password:
            self.parent.show_messagebox('warn', "错误", "请输入新主密码")
            return
            
        if not self.parent.is_password_strong(new_password):
            self.parent.show_messagebox('warn', "密码强度不足",
                "新主密码不符合要求，请确保：\n\n"
                "• 至少8个字符\n"
                "• 包含大写字母\n"
                "• 包含小写字母\n"
                "• 包含数字\n"
                "• 包含特殊字符（如：!@#$%^&*等）\n\n"
                "请重新设置一个更安全的主密码。"
            )
            return
            
        if new_password != confirm_password:
            self.parent.show_messagebox('warn', "错误", "两次输入的新密码不一致")
            return
            
        try:
            # 验证当前密码
            key = PBKDF2(current_password.encode(), self.parent.salt, dkLen=32)
            with open('master.key', 'rb') as f:
                stored_key = f.read()
            if key != stored_key:
                self.parent.show_messagebox('warn', "错误", "当前主密码不正确")
                return
                
            # 更新主密码
            self.parent.master_password = new_password
            self.parent.save_master_key()
            
            # 清空输入框
            self.current_password_edit.clear()
            self.new_password_edit.clear()
            self.confirm_password_edit.clear()
            
            self.parent.show_messagebox('info', "成功", "主密码修改成功！\n\n请务必记住您的主密码，如果忘记将无法恢复您的密码数据。")
            
        except Exception as e:
            self.parent.show_messagebox('crit', "错误", f"修改主密码时发生错误：{str(e)}")

class ShareDialog(QDialog):
    def __init__(self, parent=None, password_data=None):
        super().__init__(parent)
        self.password_data = password_data
        self.server = None
        self.server_thread = None
        self.share_path = self.generate_random_path()  # 生成随机路径
        self.is_sharing = False  # 添加分享状态标志
        self.setup_ui()
        
    def generate_random_path(self):
        """生成随机路径"""
        import random
        import string
        # 生成8位随机字符串作为路径
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(8))
        
    def setup_ui(self):
        self.setWindowTitle("分享密码")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 显示要分享的密码标题
        title_label = QLabel(f"正在分享: {self.password_data['title']}")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 网络地址信息
        network_group = QGroupBox("访问地址")
        network_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        network_layout = QVBoxLayout()
        
        # 局域网地址
        lan_layout = QHBoxLayout()
        lan_label = QLabel("局域网地址:")
        self.lan_edit = QLineEdit()
        self.lan_edit.setReadOnly(True)
        self.lan_edit.setText(self.get_local_ip())
        lan_copy_btn = QPushButton("复制")
        lan_copy_btn.setObjectName("copyBtn")
        lan_copy_btn.clicked.connect(lambda: self.copy_address("lan"))
        lan_layout.addWidget(lan_label)
        lan_layout.addWidget(self.lan_edit)
        lan_layout.addWidget(lan_copy_btn)
        network_layout.addLayout(lan_layout)
        
        # 端口信息
        port_layout = QHBoxLayout()
        port_label = QLabel("端口:")
        self.port_edit = QLineEdit()
        self.port_edit.setReadOnly(True)
        self.port_edit.setText("8080")  # 使用更常用的端口
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_edit)
        network_layout.addLayout(port_layout)
        
        # 访问路径
        path_layout = QHBoxLayout()
        path_label = QLabel("访问路径:")
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setText(self.share_path)
        path_copy_btn = QPushButton("复制")
        path_copy_btn.setObjectName("copyBtn")
        path_copy_btn.clicked.connect(lambda: self.copy_address("path"))
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_copy_btn)
        network_layout.addLayout(path_layout)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 二维码显示区域
        self.qr_label = QLabel()
        self.qr_label.setObjectName("qrLabel")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(200, 200)
        self.qr_label.hide()
        layout.addWidget(self.qr_label)
        
        # 状态标签
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        # 错误标签
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.share_btn = QPushButton("开始分享")
        self.share_btn.setObjectName("shareBtn")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        
        self.share_btn.clicked.connect(self.toggle_sharing)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.share_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: "Microsoft YaHei", "微软雅黑";
            }
            QLabel {
                font-size: 14px;
                color: #2c3e50;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #7eb9ff;
                background-color: #ffffff;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                min-width: 90px;
                font-weight: 500;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                opacity: 0.8;
            }
            QPushButton#copyBtn {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton#copyBtn:hover {
                background-color: #43A047;
            }
            QPushButton#shareBtn {
                background-color: #2196F3;
                color: white;
            }
            QPushButton#shareBtn:hover {
                background-color: #1E88E5;
            }
            QPushButton#shareBtn:checked {
                background-color: #F44336;
            }
            QPushButton#shareBtn:checked:hover {
                background-color: #E53935;
            }
            QPushButton#cancelBtn {
                background-color: #9E9E9E;
                color: white;
            }
            QPushButton#cancelBtn:hover {
                background-color: #757575;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: 500;
                color: #2c3e50;
            }
            QLabel#statusLabel {
                color: #4CAF50;
                font-size: 13px;
            }
            QLabel#errorLabel {
                color: #f44336;
                font-size: 13px;
            }
            QLabel#qrLabel {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
            }
        """)
    
    def toggle_sharing(self):
        """切换分享状态"""
        if not self.is_sharing:
            self.start_sharing()
        else:
            self.stop_sharing()
    
    def start_sharing(self):
        try:
            # 创建临时文件存储要分享的密码数据
            share_data = {
                'title': self.password_data['title'],
                'username': self.password_data['username'],
                'password': self.password_data['password'],
                'url': self.password_data.get('url', ''),
                'notes': self.password_data.get('notes', ''),
                'timestamp': str(datetime.now())
            }
            
            # 使用随机路径作为文件名
            share_file = f'share_{self.share_path}.json'
            with open(share_file, 'w', encoding='utf-8') as f:
                json.dump(share_data, f, ensure_ascii=False, indent=2)
            
            # 启动HTTP服务器，监听所有网络接口
            port = int(self.port_edit.text())
            self.server = HTTPServer(('0.0.0.0', port), ShareRequestHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # 生成并显示二维码（默认使用局域网地址）
            share_url = f"http://{self.lan_edit.text()}:{port}/{self.share_path}"
            self.generate_qr_code(share_url)
            
            self.status_label.setText("分享已启动，可以通过局域网访问")
            self.status_label.show()
            self.error_label.hide()
            
            # 更新按钮状态
            self.is_sharing = True
            self.share_btn.setText("停止分享")
            self.share_btn.setChecked(True)
            
        except Exception as e:
            self.error_label.setText(f"启动分享失败: {str(e)}")
            self.error_label.show()
            self.status_label.hide()
            self.qr_label.hide()
    
    def stop_sharing(self):
        """停止分享"""
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            # 清理分享文件
            share_file = f'share_{self.share_path}.json'
            if os.path.exists(share_file):
                os.remove(share_file)
            
            self.status_label.setText("分享已停止")
            self.qr_label.hide()
            
            # 更新按钮状态
            self.is_sharing = False
            self.share_btn.setText("开始分享")
            self.share_btn.setChecked(False)
            
        except Exception as e:
            self.error_label.setText(f"停止分享失败: {str(e)}")
            self.error_label.show()
    
    def closeEvent(self, event):
        # 关闭对话框时停止服务器
        self.stop_sharing()
        super().closeEvent(event)
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def copy_address(self, address_type="lan"):
        if address_type == "lan":
            address = f"http://{self.lan_edit.text()}:{self.port_edit.text()}/{self.share_path}"
        else:  # path
            address = self.share_path
        QApplication.clipboard().setText(address)
        self.status_label.setText("地址已复制到剪贴板")
        self.status_label.show()
        self.error_label.hide()
        
        # 生成二维码
        if address_type == "lan":
            self.generate_qr_code(address)
    
    def generate_qr_code(self, url):
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # 创建二维码图片
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为QPixmap并显示
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            qr_image.save(buffer, "PNG")
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.data())
            
            # 调整大小并显示
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.qr_label.setPixmap(scaled_pixmap)
            self.qr_label.show()
            
        except Exception as e:
            self.error_label.setText(f"生成二维码失败: {str(e)}")
            self.error_label.show()
            self.qr_label.hide()

class ShareRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # 从路径中提取分享ID
        path = self.path.lstrip('/')
        if not path:
            self.send_error(404, "Not Found")
            return
            
        share_file = f'share_{path}.json'
        if not os.path.exists(share_file):
            self.send_error(404, "分享不存在或已过期")
            return
            
        try:
            with open(share_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 生成HTML页面
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>密码分享</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: "Microsoft YaHei", "微软雅黑", -apple-system, BlinkMacSystemFont, sans-serif;
                        background-color: #f5f5f5;
                        color: #333;
                        line-height: 1.6;
                        padding: 20px;
                        max-width: 600px;
                        margin: 0 auto;
                    }}
                    .container {{
                        background-color: white;
                        border-radius: 12px;
                        box-shadow: 0 2px 12px rgba(0,0,0,0.1);
                        padding: 24px;
                        margin-top: 20px;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 24px;
                        padding-bottom: 16px;
                        border-bottom: 2px solid #f0f0f0;
                    }}
                    .header h1 {{
                        color: #2196f3;
                        font-size: 24px;
                        margin-bottom: 8px;
                    }}
                    .header .timestamp {{
                        color: #757575;
                        font-size: 14px;
                    }}
                    .info-group {{
                        background-color: #f8f9fa;
                        border-radius: 8px;
                        padding: 16px;
                        margin-bottom: 16px;
                        position: relative;
                    }}
                    .info-group:hover {{
                        background-color: #f0f7ff;
                    }}
                    .label {{
                        font-weight: 600;
                        color: #2c3e50;
                        margin-bottom: 8px;
                        display: block;
                    }}
                    .value {{
                        color: #34495e;
                        word-break: break-all;
                        padding-right: 40px;
                    }}
                    .copy-btn {{
                        position: absolute;
                        right: 12px;
                        top: 50%;
                        transform: translateY(-50%);
                        background-color: #2196f3;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 13px;
                        cursor: pointer;
                        transition: background-color 0.2s;
                    }}
                    .copy-btn:hover {{
                        background-color: #1976d2;
                    }}
                    .copy-btn.copied {{
                        background-color: #4caf50;
                    }}
                    .url-link {{
                        color: #2196f3;
                        text-decoration: none;
                        word-break: break-all;
                    }}
                    .url-link:hover {{
                        text-decoration: underline;
                    }}
                    .notes {{
                        white-space: pre-wrap;
                        background-color: #fff;
                        padding: 12px;
                        border-radius: 4px;
                        border: 1px solid #e0e0e0;
                        margin-top: 8px;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 24px;
                        color: #757575;
                        font-size: 13px;
                    }}
                    @media (max-width: 480px) {{
                        body {{
                            padding: 12px;
                        }}
                        .container {{
                            padding: 16px;
                        }}
                        .header h1 {{
                            font-size: 20px;
                        }}
                        .copy-btn {{
                            padding: 4px 8px;
                            font-size: 12px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{data['title']}</h1>
                        <div class="timestamp">分享时间：{data['timestamp']}</div>
                    </div>
                    
                    <div class="info-group">
                        <span class="label">用户名</span>
                        <span class="value" id="username">{data['username']}</span>
                        <button class="copy-btn" onclick="copyText('username')">复制</button>
                    </div>
                    
                    <div class="info-group">
                        <span class="label">密码</span>
                        <span class="value" id="password">{data['password']}</span>
                        <button class="copy-btn" onclick="copyText('password')">复制</button>
                    </div>
            """
            
            if data.get('url'):
                html += f"""
                    <div class="info-group">
                        <span class="label">登录地址</span>
                        <a href="{data['url']}" class="url-link" target="_blank" id="url">{data['url']}</a>
                        <button class="copy-btn" onclick="copyText('url')">复制</button>
                    </div>
                """
            
            if data.get('notes'):
                html += f"""
                    <div class="info-group">
                        <span class="label">备注</span>
                        <div class="notes">{data['notes']}</div>
                    </div>
                """
            
            html += """
                    <div class="footer">
                        密码分享页面 - 请勿在公共网络分享
                    </div>
                </div>
                
                <script>
                    function copyText(elementId) {
                        const element = document.getElementById(elementId);
                        const text = element.textContent;
                        const btn = element.nextElementSibling;
                        
                        // 复制到剪贴板
                        navigator.clipboard.writeText(text).then(() => {
                            // 更新按钮状态
                            btn.textContent = '已复制';
                            btn.classList.add('copied');
                            
                            // 2秒后恢复按钮状态
                            setTimeout(() => {
                                btn.textContent = '复制';
                                btn.classList.remove('copied');
                            }, 2000);
                        }).catch(err => {
                            console.error('复制失败:', err);
                            alert('复制失败，请手动复制');
                        });
                    }
                </script>
            </body>
            </html>
            """
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, str(e))

class PasswordManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.passwords = []
        self.groups = ["默认分组"]  # 默认分组
        self.current_group = "默认分组"
        self.data_file = 'passwords.json'
        self.master_password = None
        self.salt = None
        self.is_dark_mode = False  # 添加主题状态
        
        # 初始化全局快捷键
        self.global_shortcuts = {}
        self.setup_global_shortcuts()
        
        # 先初始化加密，再设置UI
        self.initialize_encryption()
        self.setup_ui()
        self.setup_style()
        self.load_data()
        # 确保在启动时显示教程
        self.password_list.clearSelection()
        self.show_password_details(None, None)
        
    def setup_global_shortcuts(self):
        """设置全局快捷键"""
        try:
            # 加载快捷键设置
            if os.path.exists('shortcuts.json'):
                with open('shortcuts.json', 'r', encoding='utf-8') as f:
                    shortcuts = json.load(f)
            else:
                shortcuts = {
                    'global_search': 'Ctrl+Alt+F',
                    'global_lock': 'Ctrl+Alt+L',
                    'global_show': 'Ctrl+Alt+S',
                    'global_hide': 'Ctrl+Alt+H',
                    'app_search': 'Ctrl+F',
                    'app_add': 'Ctrl+N'
                }
            
            # 创建全局快捷键
            self.global_shortcuts = {
                'global_search': QShortcut(QKeySequence(shortcuts['global_search']), self),
                'global_lock': QShortcut(QKeySequence(shortcuts['global_lock']), self),
                'global_show': QShortcut(QKeySequence(shortcuts['global_show']), self),
                'global_hide': QShortcut(QKeySequence(shortcuts['global_hide']), self),
                'app_search': QShortcut(QKeySequence(shortcuts['app_search']), self),
                'app_add': QShortcut(QKeySequence(shortcuts['app_add']), self)
            }
            
            # 连接信号
            self.global_shortcuts['global_search'].activated.connect(self.show_global_search)
            self.global_shortcuts['global_lock'].activated.connect(self.lock_application)
            self.global_shortcuts['global_show'].activated.connect(self.show_application)
            self.global_shortcuts['global_hide'].activated.connect(self.hide_application)
            self.global_shortcuts['app_search'].activated.connect(self.focus_search)
            self.global_shortcuts['app_add'].activated.connect(self.new_password)
            
        except Exception as e:
            self.show_messagebox('warn', "错误", f"设置全局快捷键失败：{str(e)}")
            
    def show_global_search(self):
        """显示全局搜索窗口"""
        if not self.isVisible():
            self.show()
        self.activateWindow()
        self.search_input.setFocus()
        
    def lock_application(self):
        """锁定应用程序"""
        self.hide()
        # 这里可以添加锁定逻辑，比如要求重新输入主密码
        
    def show_application(self):
        """显示应用程序"""
        self.show()
        self.activateWindow()
        
    def hide_application(self):
        """隐藏应用程序"""
        self.hide()
        
    def focus_search(self):
        """聚焦到搜索框"""
        self.search_input.setFocus()
        
    def update_shortcuts(self):
        """更新快捷键设置"""
        try:
            # 加载新的快捷键设置
            with open('shortcuts.json', 'r', encoding='utf-8') as f:
                shortcuts = json.load(f)
            
            # 更新全局快捷键
            for key, shortcut in self.global_shortcuts.items():
                shortcut.setKey(QKeySequence(shortcuts[key]))
                
        except Exception as e:
            self.show_messagebox('warn', "错误", f"更新快捷键设置失败：{str(e)}")
            
    def setup_style(self):
        # 定义亮色主题样式
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #ffffff;
                color: #2c3e50;
                font-family: "Microsoft YaHei", "微软雅黑";
            }
            QWidget#leftPanel {
                background-color: #f8f9fa;
                border-right: 1px solid #e9ecef;
            }
            QWidget#rightPanel {
                background-color: #ffffff;
            }
            QPushButton#newBtn {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                min-width: 120px;
                font-weight: 500;
                margin: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton#newBtn:hover {
                background-color: #43A047;
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                font-size: 14px;
                min-height: 20px;
                margin: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
                background-color: #ffffff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                min-width: 100px;
                font-weight: 500;
                transition: all 0.3s;
            }
            QPushButton:hover {
                opacity: 0.9;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                opacity: 0.8;
                transform: translateY(1px);
            }
            QPushButton#editBtn {
                background-color: #2196F3;
                color: white;
                box-shadow: 0 2px 4px rgba(33,150,243,0.2);
            }
            QPushButton#editBtn:hover {
                background-color: #1E88E5;
                box-shadow: 0 4px 8px rgba(33,150,243,0.3);
            }
            QPushButton#deleteBtn {
                background-color: #F44336;
                color: white;
                box-shadow: 0 2px 4px rgba(244,67,54,0.2);
            }
            QPushButton#deleteBtn:hover {
                background-color: #E53935;
                box-shadow: 0 4px 8px rgba(244,67,54,0.3);
            }
            QPushButton#settingsBtn {
                background-color: #607D8B;
                color: white;
                box-shadow: 0 2px 4px rgba(96,125,139,0.2);
            }
            QPushButton#settingsBtn:hover {
                background-color: #546E7A;
                box-shadow: 0 4px 8px rgba(96,125,139,0.3);
            }
            QPushButton#shareBtn {
                background-color: #4CAF50;
                color: white;
                box-shadow: 0 2px 4px rgba(76,175,80,0.2);
            }
            QPushButton#shareBtn:hover {
                background-color: #43A047;
                box-shadow: 0 4px 8px rgba(76,175,80,0.3);
            }
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
                font-size: 14px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 12px 15px;
                margin: 2px 5px;
                border-radius: 6px;
                color: #2c3e50;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 12px;
                font-size: 14px;
                selection-background-color: #a8d8ff;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }
            QTextEdit:focus {
                border: 2px solid #4CAF50;
                background-color: #ffffff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdbdbd;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9e9e9e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QLabel#detailLabel {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 20px;
                font-size: 14px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
        """)

    def setup_ui(self):
        self.setWindowTitle("密码管理器")
        self.setMinimumSize(1000, 600)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        main_widget.setLayout(layout)
        
        # 左侧面板
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_panel.setObjectName("leftPanel")  # 添加对象名以便设置样式
        left_layout = QVBoxLayout()
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_panel.setLayout(left_layout)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索密码...")
        self.search_input.textChanged.connect(self.search_passwords)
        self.search_input.setStyleSheet("""
            QLineEdit {
                margin: 15px;
                border-radius: 6px;
            }
        """)
        
        # 密码列表
        self.password_list = QListWidget()
        self.password_list.setAlternatingRowColors(True)
        self.password_list.currentItemChanged.connect(self.show_password_details)
        
        # 新建密码按钮
        new_btn = QPushButton("新建密码")
        new_btn.clicked.connect(self.new_password)
        new_btn.setObjectName("newBtn")  # 添加对象名以便设置样式
        new_btn.setStyleSheet("""
            QPushButton {
                margin: 15px;
            }
        """)
        
        # 添加到左侧布局
        left_layout.addWidget(self.search_input)
        left_layout.addWidget(self.password_list)
        left_layout.addWidget(new_btn)
        
        # 右侧面板
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")  # 添加对象名以便设置样式
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(30, 30, 30, 30)
        right_panel.setLayout(right_layout)
        
        # 详情内容
        self.details_label = QLabel()
        self.details_label.setObjectName("detailLabel")
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.details_label.setWordWrap(True)
        self.details_label.setTextFormat(Qt.TextFormat.RichText)
        self.details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByKeyboard
        )
        self.details_label.linkActivated.connect(self.handle_link_click)
        self.details_label.mousePressEvent = self.handle_mouse_press
        
        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.edit_btn = QPushButton("修改")
        self.delete_btn = QPushButton("删除")
        self.settings_btn = QPushButton("设置")
        self.share_btn = QPushButton("分享")  # 新增分享按钮
        
        # 设置按钮对象名
        self.edit_btn.setObjectName("editBtn")
        self.delete_btn.setObjectName("deleteBtn")
        self.settings_btn.setObjectName("settingsBtn")
        self.share_btn.setObjectName("shareBtn")  # 设置分享按钮样式
        
        self.edit_btn.clicked.connect(self.edit_password)
        self.delete_btn.clicked.connect(self.delete_password)
        self.settings_btn.clicked.connect(self.show_settings)
        self.share_btn.clicked.connect(self.share_password)  # 连接分享功能
        
        button_layout.addStretch()
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.share_btn)  # 添加分享按钮
        button_layout.addWidget(self.settings_btn)
        
        # 添加到右侧布局
        right_layout.addWidget(self.details_label)
        right_layout.addStretch()
        right_layout.addLayout(button_layout)
        
        # 添加到主布局
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)

    def initialize_encryption(self):
        """初始化加密系统"""
        try:
            # 生成或加载盐值
            if os.path.exists('salt.bin'):
                with open('salt.bin', 'rb') as f:
                    self.salt = f.read()
            else:
                self.salt = get_random_bytes(32)
                with open('salt.bin', 'wb') as f:
                    f.write(self.salt)
            
            # 检查主密码文件
            if not os.path.exists('master.key'):
                # 首次运行时要求用户设置主密码
                self.set_master_password()
            else:
                # 验证主密码
                self.verify_master_password()
                
            # 确保主密码已设置
            if not self.master_password:
                QMessageBox.critical(
                    self, "错误",
                    "主密码设置失败，程序将退出。\n\n" +
                    "如果问题持续存在，请删除 master.key 和 salt.bin 文件后重试。"
                )
                sys.exit(1)
                
        except Exception as e:
            QMessageBox.critical(
                self, "初始化失败",
                f"初始化加密系统时发生错误：\n{str(e)}\n\n" +
                "程序将退出。如果问题持续存在，请删除 master.key 和 salt.bin 文件后重试。"
            )
            sys.exit(1)

    def set_master_password(self):
        """设置主密码"""
        try:
            while True:
                password, ok = self.get_text_input(
                    "设置主密码",
                    "欢迎使用密码管理器！\n\n"
                    "首次使用需要设置主密码，用于加密所有密码数据。\n\n"
                    "主密码要求：\n"
                    "• 至少8个字符\n"
                    "• 包含大写字母\n"
                    "• 包含小写字母\n"
                    "• 包含数字\n"
                    "• 包含特殊字符（如：!@#$%^&*等）\n\n"
                    "请设置您的主密码：",
                    QLineEdit.EchoMode.Password
                )
                if not ok:
                    box = QMessageBox(self)
                    box.setWindowTitle("确认退出")
                    box.setText("您确定要退出程序吗？\n如果不设置主密码，将无法使用密码管理器。")
                    if self.is_dark_mode:
                        box.setStyleSheet("""
                            QMessageBox { background-color: #23272e; color: #e0e0e0; }
                            QLabel { color: #e0e0e0; }
                            QPushButton { background-color: #424242; color: #e0e0e0; border-radius: 6px; padding: 8px 18px; }
                            QPushButton:hover { background-color: #616161; }
                        """)
                    box.setIcon(QMessageBox.Icon.Question)
                    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    box.setDefaultButton(QMessageBox.StandardButton.No)
                    reply = box.exec()
                    if reply == QMessageBox.StandardButton.Yes:
                        sys.exit(0)
                    continue
                if not password:  # 检查密码是否为空
                    self.show_messagebox('warn', "密码为空", "主密码不能为空，请重新输入。")
                    continue
                if not self.is_password_strong(password):
                    self.show_messagebox('warn', "密码强度不足",
                        "您设置的主密码不符合要求，请确保：\n\n"
                        "• 至少8个字符\n"
                        "• 包含大写字母\n"
                        "• 包含小写字母\n"
                        "• 包含数字\n"
                        "• 包含特殊字符（如：!@#$%^&*等）\n\n"
                        "请重新设置一个更安全的主密码。"
                    )
                    continue
                confirm, ok = self.get_text_input(
                    "确认主密码",
                    "为了确保您记住了主密码，请再次输入：",
                    QLineEdit.EchoMode.Password
                )
                if not ok:
                    continue
                if not confirm:  # 检查确认密码是否为空
                    self.show_messagebox('warn', "密码为空", "确认密码不能为空，请重新输入。")
                    continue
                if password != confirm:
                    self.show_messagebox('warn', "密码不匹配", "两次输入的密码不一致，请重新设置。")
                    continue
                try:
                    self.master_password = password
                    self.save_master_key()
                    self.show_messagebox('info', "设置成功", "主密码设置成功！\n\n请务必记住您的主密码，如果忘记将无法恢复您的密码数据。")
                    break
                except Exception as e:
                    self.show_messagebox('crit', "保存失败", f"保存主密码时发生错误：\n{str(e)}\n\n请重试。如果问题持续存在，请联系技术支持。")
                    continue
        except Exception as e:
            self.show_messagebox('crit', "设置失败", f"设置主密码时发生错误：\n{str(e)}\n\n请重试。如果问题持续存在，请联系技术支持。")
            sys.exit(1)

    def verify_master_password(self):
        """验证主密码"""
        while True:
            password, ok = self.get_text_input(
                "验证主密码",
                "请输入您的主密码以解锁密码管理器：",
                QLineEdit.EchoMode.Password
            )
            if not ok:
                box = QMessageBox(self)
                box.setWindowTitle("确认退出")
                box.setText("您确定要退出程序吗？\n如果不输入主密码，将无法访问您的密码数据。")
                box.setIcon(QMessageBox.Icon.Question)
                box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                box.setDefaultButton(QMessageBox.StandardButton.No)
                
                # 设置按钮样式
                for btn in box.buttons():
                    if btn.text() in ["&Yes", "Yes", "是"]:
                        btn.setStyleSheet("""
                            QPushButton {
                                background-color: #2196f3;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                padding: 8px 18px;
                                font-size: 14px;
                                min-width: 80px;
                            }
                            QPushButton:hover {
                                background-color: #1976d2;
                            }
                        """)
                    elif btn.text() in ["&No", "No", "否"]:
                        btn.setStyleSheet("""
                            QPushButton {
                                background-color: #9E9E9E;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                padding: 8px 18px;
                                font-size: 14px;
                                min-width: 80px;
                            }
                            QPushButton:hover {
                                background-color: #757575;
                            }
                        """)
                
                reply = box.exec()
                if reply == QMessageBox.StandardButton.Yes:
                    sys.exit(0)
                continue
            key = PBKDF2(password.encode(), self.salt, dkLen=32)
            try:
                with open('master.key', 'rb') as f:
                    stored_key = f.read()
                if key == stored_key:
                    self.master_password = password
                    break
                else:
                    self.show_messagebox('warn', "密码错误", "您输入的主密码不正确，请重试。\n\n如果忘记主密码，将无法恢复您的密码数据。")
            except Exception as e:
                self.show_messagebox('crit', "验证失败", f"验证主密码时发生错误：\n{str(e)}\n\n如果问题持续存在，请联系技术支持。")
                sys.exit(1)

    def is_password_strong(self, password):
        """检查密码强度"""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False
        return True

    def save_master_key(self):
        """保存主密码密钥"""
        try:
            key = PBKDF2(self.master_password.encode(), self.salt, dkLen=32)
            with open('master.key', 'wb') as f:
                f.write(key)
        except Exception as e:
            self.show_messagebox('crit', "错误", f"保存主密码密钥时发生错误：{str(e)}")
            sys.exit(1)

    def encrypt_data(self, data):
        """加密数据"""
        try:
            # 使用 PBKDF2 生成密钥
            key = PBKDF2(self.master_password.encode(), self.salt, dkLen=32)
            
            # 生成随机 IV
            iv = get_random_bytes(AES.block_size)
            
            # 创建加密器
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # 加密数据
            json_data = json.dumps(data).encode('utf-8')
            padded_data = pad(json_data, AES.block_size)
            ct_bytes = cipher.encrypt(padded_data)
            
            # 组合 IV 和密文
            encrypted_data = {
                'iv': base64.b64encode(iv).decode('utf-8'),
                'ciphertext': base64.b64encode(ct_bytes).decode('utf-8'),
                'version': '1.0'  # 添加版本号以便将来升级加密方案
            }
            
            return json.dumps(encrypted_data)
        except Exception as e:
            self.show_messagebox('crit', "错误", f"加密数据时发生错误：{str(e)}")
            return None

    def decrypt_data(self, encrypted_data):
        """解密数据"""
        try:
            # 尝试解析为新格式
            try:
                data = json.loads(encrypted_data)
                # 检查版本（如果没有version字段，默认为1.0）
                version = data.get('version', '1.0')
                if version != '1.0':
                    raise ValueError(f"不支持的加密版本: {version}")
                # 解码 IV 和密文
                iv = base64.b64decode(data['iv'])
                ct = base64.b64decode(data['ciphertext'])
                # 使用 PBKDF2 生成密钥
                key = PBKDF2(self.master_password.encode(), self.salt, dkLen=32)
                # 创建解密器
                cipher = AES.new(key, AES.MODE_CBC, iv)
                # 解密数据
                pt = unpad(cipher.decrypt(ct), AES.block_size)
                return json.loads(pt.decode('utf-8'))
            except (json.JSONDecodeError, KeyError, TypeError):
                # 如果不是JSON格式或缺少字段，尝试作为旧格式处理
                try:
                    ct = base64.b64decode(encrypted_data)
                    key = PBKDF2(self.master_password.encode(), self.salt, dkLen=32)
                    cipher = AES.new(key, AES.MODE_CBC, ct[:16])  # 前16字节作为IV
                    pt = unpad(cipher.decrypt(ct[16:]), AES.block_size)
                    return json.loads(pt.decode('utf-8'))
                except Exception as e:
                    raise ValueError(f"解密旧版本数据失败: {str(e)}")
        except Exception as e:
            self.show_messagebox('crit', "错误", f"解密数据时发生错误：{str(e)}")
            return []  # 确保返回空列表而不是 None

    def load_data(self):
        """加载密码数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                    if not encrypted_data:  # 如果文件为空
                        self.passwords = []
                        return
                    decrypted_data = self.decrypt_data(encrypted_data)
                    if decrypted_data is None:  # 如果解密失败
                        self.passwords = []
                        return
                    self.passwords = decrypted_data
                # 收集所有分组
                all_groups = set([p.get("group", "默认分组") for p in self.passwords])
                self.groups = ["默认分组"] + [g for g in all_groups if g != "默认分组"]
                self.password_list.clear()
                self.password_list.addItems(self.groups)
                self.update_list()
            except Exception as e:
                self.show_messagebox('warn', "错误", f"加载密码失败: {str(e)}")
                self.passwords = []
        else:
            self.passwords = []
            self.save_passwords()
    
    def save_passwords(self):
        """保存密码数据"""
        try:
            encrypted_data = self.encrypt_data(self.passwords)
            if encrypted_data:
                # 使用临时文件进行原子写入
                temp_file = self.data_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted_data)
                # 原子性地替换原文件
                os.replace(temp_file, self.data_file)
        except Exception as e:
            self.show_messagebox('crit', "错误", f"保存密码数据时发生错误：{str(e)}")
    
    def update_list(self):
        self.password_list.clear()
        for password in self.passwords:
            item = QListWidgetItem(password['title'])
            if password.get('group', '默认分组') != '默认分组':
                item.setText(f"{password['title']} ({password['group']})")
            self.password_list.addItem(item)
    
    def show_password_details(self, current, previous):
        if current is None:
            # 显示使用教程
            text_color = "#606266"
            border_color = "#dcdfe6"
            header_bg = "#f5f7fa"
            row_bg = "#ffffff"
            hover_bg = "#f5f7fa"
            header_text = "#909399"
            container_bg = "#ffffff"
            
            tutorial = f"""
            <div style="font-family: 'Microsoft YaHei', '微软雅黑', sans-serif; background-color: {container_bg}; padding: 20px; border-radius: 8px;">
                <table style="width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 4px; overflow: hidden; border: 1px solid {border_color};">
                    <thead>
                        <tr>
                            <th style="background-color: {header_bg}; padding: 12px 20px; text-align: left; font-weight: 500; color: {header_text}; font-size: 14px;">功能说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="background-color: {row_bg};">
                            <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; line-height: 1.5;">
                                点击左侧面板底部的"新建密码"按钮，填写密码信息并保存
                            </td>
                        </tr>
                        <tr style="background-color: {row_bg};">
                            <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; line-height: 1.5;">
                                在左侧搜索框中输入关键词，可以快速查找密码
                            </td>
                        </tr>
                        <tr style="background-color: {row_bg};">
                            <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; line-height: 1.5;">
                                选择密码项后，点击右侧的"修改"按钮进行编辑
                            </td>
                        </tr>
                        <tr style="background-color: {row_bg};">
                            <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; line-height: 1.5;">
                                选择密码项后，点击右侧的"删除"按钮删除密码
                            </td>
                        </tr>
                        <tr style="background-color: {row_bg};">
                            <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; line-height: 1.5;">
                                选择密码项后，点击右侧的"分享"按钮，可以通过局域网或热点分享密码
                            </td>
                        </tr>
                        <tr style="background-color: {row_bg};">
                            <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; line-height: 1.5;">
                                • 点击密码详情中的"复制"按钮可以快速复制内容<br>
                                • 点击"显示"按钮可以查看密码明文<br>
                                • 按住Ctrl点击登录地址可以直接打开链接
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """
            self.details_label.setText(tutorial)
            return
            
        # 密码详情显示
        index = self.password_list.row(current)
        password = self.passwords[index]
        
        # 根据当前主题设置颜色
        text_color = "#e0e0e0" if self.is_dark_mode else "#606266"
        border_color = "#424242" if self.is_dark_mode else "#dcdfe6"
        header_bg = "#2d2d2d" if self.is_dark_mode else "#f5f7fa"
        row_bg = "#1e1e1e" if self.is_dark_mode else "#ffffff"
        hover_bg = "#2d2d2d" if self.is_dark_mode else "#f5f7fa"
        header_text = "#e0e0e0" if self.is_dark_mode else "#909399"
        link_color = "#409eff" if self.is_dark_mode else "#409eff"
        copy_color = "#67c23a" if self.is_dark_mode else "#67c23a"  # 复制操作使用绿色
        show_color = "#e6a23c" if self.is_dark_mode else "#e6a23c"  # 显示操作使用橙色
        link_hover = "#66b1ff" if self.is_dark_mode else "#66b1ff"
        copy_hover = "#85ce61" if self.is_dark_mode else "#85ce61"
        show_hover = "#ebb563" if self.is_dark_mode else "#ebb563"
        
        details = f"""
        <div style="font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;">
            <table style="width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 4px; overflow: hidden;">
                <thead>
                    <tr>
                        <th style="background-color: {header_bg}; padding: 12px 20px; text-align: left; font-weight: 500; color: {header_text}; font-size: 14px; width: 120px;">字段</th>
                        <th style="background-color: {header_bg}; padding: 12px 20px; text-align: left; font-weight: 500; color: {header_text}; font-size: 14px;">内容</th>
                        <th style="background-color: {header_bg}; padding: 12px 20px; text-align: center; font-weight: 500; color: {header_text}; font-size: 14px; width: 120px;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background-color: {row_bg};">
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px;">用户名</td>
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; font-family: Consolas, Monaco, monospace;">{password["username"]}</td>
                        <td style="padding: 12px 20px; text-align: center;">
                            <a href="copy:{password["username"]}" class="el-link" style="color: {copy_color}; text-decoration: none; font-size: 14px; margin: 0 4px; transition: color 0.3s;">
                                复制
                            </a>
                        </td>
                    </tr>
                    <tr style="background-color: {row_bg};">
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px;">密码</td>
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; font-family: Consolas, Monaco, monospace;">
                            {password["password"]}
                        </td>
                        <td style="padding: 12px 20px; text-align: center;">
                            <a href="copy:{password["password"]}" class="el-link" style="color: {copy_color}; text-decoration: none; font-size: 14px; transition: color 0.3s;">
                                复制
                            </a>
                        </td>
                    </tr>
        """
        
        if password.get('url'):
            details += f"""
                    <tr style="background-color: {row_bg};">
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px;">登录地址</td>
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px;">
                            <a href="{password["url"]}" style="color: {link_color}; text-decoration: none; transition: color 0.3s;">{password["url"]}</a>
                            <span style="color: #909399; margin-left: 8px; font-size: 12px;">(按住Ctrl点击打开)</span>
                        </td>
                        <td style="padding: 12px 20px; text-align: center;">
                            <a href="copy:{password["url"]}" class="el-link" style="color: {copy_color}; text-decoration: none; font-size: 14px; transition: color 0.3s;">
                                复制
                            </a>
                        </td>
                    </tr>
            """
        
        if password.get('notes'):
            details += f"""
                    <tr style="background-color: {row_bg};">
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px;">备注</td>
                        <td style="padding: 12px 20px; color: {text_color}; font-size: 14px; white-space: pre-wrap; line-height: 1.5;">{password["notes"]}</td>
                        <td style="padding: 12px 20px; text-align: center;">
                            <a href="copy:{password["notes"]}" class="el-link" style="color: {copy_color}; text-decoration: none; font-size: 14px; transition: color 0.3s;">
                                复制
                            </a>
                        </td>
                    </tr>
            """
        
        details += """
                </tbody>
            </table>
            <style>
                tr:hover {{
                    background-color: {hover_bg} !important;
                }}
                .el-link:hover {{
                    color: {link_hover} !important;
                }}
                .el-link[href^="copy:"]:hover {{
                    color: {copy_hover} !important;
                }}
            </style>
            <script>
                // 移除不再需要的密码显示/隐藏相关代码
            </script>
        </div>
        """
        
        self.details_label.setText(details)
    
    def new_group(self):
        group_name, ok = self.get_text_input("新建分组", "请输入分组名称：")
        if ok and group_name:
            if group_name in self.groups:
                self.show_messagebox('warn', "警告", "该分组已存在！")
                return
            self.groups.append(group_name)
            self.password_list.addItem(group_name)
            self.password_list.setCurrentRow(self.password_list.count() - 1)

    def group_changed(self, current, previous):
        if current is None:
            return
        self.current_group = current.text()
        self.update_list()

    def new_password(self):
        dialog = PasswordDialog(self)
        if dialog.exec():
            password_data = {
                'title': dialog.title_edit.text(),
                'username': dialog.username_edit.text(),
                'password': dialog.password_edit.text(),
                'url': dialog.url_edit.text(),
                'notes': dialog.notes_edit.toPlainText(),
                'group': self.current_group
            }
            self.passwords.append(password_data)
            self.save_passwords()
            self.update_list()

    def edit_password(self):
        current = self.password_list.currentItem()
        if current is None:
            self.show_messagebox('warn', "警告", "请先选择一个密码项")
            return
             
        index = self.password_list.row(current)
        group_passwords = [p for p in self.passwords if p.get('group', '默认分组') == self.current_group]
        password = group_passwords[index]
        actual_index = self.passwords.index(password)
        
        dialog = PasswordDialog(self, password)
        if dialog.exec():
            self.passwords[actual_index] = {
                'title': dialog.title_edit.text(),
                'username': dialog.username_edit.text(),
                'password': dialog.password_edit.text(),
                'url': dialog.url_edit.text(),
                'notes': dialog.notes_edit.toPlainText(),
                'group': self.current_group
            }
            self.save_passwords()
            self.update_list()

    def delete_password(self):
        current = self.password_list.currentItem()
        if current is None:
            self.show_messagebox('warn', "警告", "请先选择一个密码项")
            return
             
        reply = QMessageBox.question(self, "确认", "确定要删除这个密码项吗？",
                                   QMessageBox.StandardButton.Yes | 
                                   QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            index = self.password_list.row(current)
            group_passwords = [p for p in self.passwords if p.get('group', '默认分组') == self.current_group]
            password = group_passwords[index]
            actual_index = self.passwords.index(password)
            del self.passwords[actual_index]
            self.save_passwords()
            self.update_list()

    def search_passwords(self):
        search_text = self.search_input.text().lower()
        self.password_list.clear()
        
        for password in self.passwords:
            if password.get('group', '默认分组') == self.current_group:
                if (search_text in password['title'].lower() or
                    search_text in password['username'].lower() or
                    search_text in password['notes'].lower()):
                    self.password_list.addItem(password['title'])

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.theme_btn.setText("☀️" if self.is_dark_mode else "🌙")
        self.setStyleSheet(self.dark_style if self.is_dark_mode else self.light_style)
        
        # 更新详情显示以适应新主题
        current_item = self.password_list.currentItem()
        if current_item:
            self.show_password_details(current_item, None)

    def handle_link_click(self, url):
        if url.startswith("copy:"):
            QApplication.clipboard().setText(url[5:])
            self.show_messagebox('info', "提示", "已复制到剪贴板")
        elif url.startswith("http"):
            webbrowser.open(url)

    def handle_mouse_press(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # 获取点击位置的文本
            pos = event.pos()
            text = self.details_label.text()
            
            # 检查是否点击了链接
            if '<a href="' in text:
                # 使用简单的文本匹配来查找链接
                start = text.find('<a href="', pos.x())
                if start != -1:
                    end = text.find('">', start)
                    if end != -1:
                        url = text[start + 9:end]
                        if url.startswith("http"):
                            webbrowser.open(url)
        else:
            # 正常的选择文本行为
            super().mousePressEvent(event)

    def share_password(self):
        current = self.password_list.currentItem()
        if current is None:
            self.show_messagebox('warn', "警告", "请先选择一个密码项")
            return
             
        index = self.password_list.row(current)
        password = self.passwords[index]
        
        dialog = ShareDialog(self, password)
        dialog.exec()
        
        # 清理临时文件
        try:
            if os.path.exists('share_temp.json'):
                os.remove('share_temp.json')
        except:
            pass

    def show_messagebox(self, mtype, title, text):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        # 根据类型设置按钮
        if mtype == 'info':
            box.setIcon(QMessageBox.Icon.Information)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
        elif mtype == 'warn':
            box.setIcon(QMessageBox.Icon.Warning)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
        elif mtype == 'crit':
            box.setIcon(QMessageBox.Icon.Critical)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
        elif mtype == 'yesno':
            box.setIcon(QMessageBox.Icon.Question)
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        else:
            box.setIcon(QMessageBox.Icon.NoIcon)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # 主题样式
        if self.is_dark_mode:
            box.setStyleSheet("""
                QMessageBox {
                    background-color: #23272e;
                    color: #e0e0e0;
                    font-family: 'Microsoft YaHei', '微软雅黑';
                }
                QLabel {
                    color: #e0e0e0;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    border: none;
                    border-radius: 6px;
                    padding: 8px 18px;
                    font-size: 14px;
                    min-width: 80px;
                }
                QPushButton:enabled {
                    background-color: #424242;
                    color: #e0e0e0;
                }
                QPushButton:enabled:focus {
                    outline: 2px solid #2196f3;
                }
                QPushButton:hover {
                    background-color: #616161;
                }
            """)
        else:
            box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #2c3e50;
                    font-family: 'Microsoft YaHei', '微软雅黑';
                }
                QLabel {
                    color: #2c3e50;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    border: none;
                    border-radius: 6px;
                    padding: 8px 18px;
                    font-size: 14px;
                    min-width: 80px;
                }
                QPushButton:enabled {
                    background-color: #f0f0f0;
                    color: #2c3e50;
                }
                QPushButton:enabled:focus {
                    outline: 2px solid #2196f3;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
        # 按钮着色
        for btn in box.buttons():
            role = box.buttonRole(btn)
            if btn.text() in ["&Yes", "Yes", "确定", "OK", "&OK"]:
                btn.setStyleSheet("background-color: #2196f3; color: #fff;" if not self.is_dark_mode else "background-color: #2196f3; color: #fff;")
            elif btn.text() in ["&No", "No", "取消", "Cancel", "&Cancel"]:
                btn.setStyleSheet("background-color: #9E9E9E; color: #fff;" if not self.is_dark_mode else "background-color: #9E9E9E; color: #fff;")
        return box.exec()

    def get_text_input(self, title, label, echo=QLineEdit.EchoMode.Normal):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextEchoMode(echo)
        
        # 设置对话框样式
        dialog.setStyleSheet("""
            QInputDialog {
                background-color: #ffffff;
                color: #2c3e50;
                font-family: 'Microsoft YaHei', '微软雅黑';
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                padding: 10px;
            }
            QLineEdit {
                background-color: #f8f9fa;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
                background-color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 14px;
                min-width: 80px;
            }
        """)
            
        # 设置按钮颜色
        for btn in dialog.findChildren(QPushButton):
            if btn.text() in ["确定", "OK", "&OK"]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2196f3;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 18px;
                        font-size: 14px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #1976d2;
                    }
                """)
            elif btn.text() in ["取消", "Cancel", "&Cancel"]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #9E9E9E;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 18px;
                        font-size: 14px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #757575;
                    }
                """)
            
        ok = dialog.exec()
        return dialog.textValue(), ok == QDialog.DialogCode.Accepted

def main():
    app = QApplication(sys.argv)
    window = PasswordManager()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序发生错误: {str(e)}")
        input("按回车键退出...") 