import sys
import os
import pyperclip
import mouse
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSizeGrip, QFrame, QScrollArea, 
                             QPushButton, QMenu, QAction, QSystemTrayIcon, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QPixmap
from deep_translator import GoogleTranslator

LANGUAGES = [
    ("한국어 (Korean)", "ko"),
    ("영어 (English)", "en"),
    ("일본어 (Japanese)", "ja"),
    ("중국어 간체 (Chinese)", "zh-CN"),
    ("프랑스어 (French)", "fr"),
    ("독일어 (German)", "de")
]

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class TranslationThread(QThread):
    finished_signal = pyqtSignal(str, str)  
    error_signal = pyqtSignal(str)          

    def __init__(self, text, source_lang, target_lang):
        super().__init__()
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang

    def run(self):
        try:
            translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
            result = translator.translate(self.text)
            if result:
                self.finished_signal.emit(self.text, result)
            else:
                self.error_signal.emit("⚠️ 번역 결과가 비어있습니다.")
        except Exception as e:
            self.error_signal.emit(f"❌ 오류 발생:\n{str(e)}")


class ManualTranslatorWindow(QWidget):
    def __init__(self, main_icon_pixmap, main_window):
        super().__init__()
        self.main_icon_pixmap = main_icon_pixmap
        self.main_window = main_window 
        self.moving = False
        self.offset = QPoint()
        self.manual_result_pure = "" 
        self.trans_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_frame = QFrame(self)
        self.bg_frame.setStyleSheet("QFrame { background-color: rgba(35, 35, 35, 240); border: 2px solid #777777; border-radius: 12px; }")
        
        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(15, 10, 15, 5)
        
        title_layout = QHBoxLayout()
        self.title_icon = QLabel(self)
        if not self.main_icon_pixmap.isNull():
            self.title_icon.setPixmap(self.main_icon_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.title_icon.setText("✏️")
        title_layout.addWidget(self.title_icon)
        
        self.title_text = QLabel("ClipTrans - 수동 번역", self)
        self.title_text.setStyleSheet("QLabel { color: #BBBBBB; font-size: 12px; font-family: 'Malgun Gothic'; font-weight: bold; border: none; }")
        title_layout.addWidget(self.title_text)
        title_layout.addStretch()
        
        self.btn_close = QPushButton("×", self)
        self.btn_close.setFixedSize(28, 22)
        self.btn_close.setStyleSheet("QPushButton { color: #AAAAAA; font-size: 16px; font-weight: bold; background-color: transparent; border: none; border-radius: 4px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(240, 71, 71, 200); }")
        self.btn_close.clicked.connect(self.hide)
        title_layout.addWidget(self.btn_close)
        frame_layout.addLayout(title_layout)
        
        self.input_edit = QTextEdit(self)
        self.input_edit.setPlaceholderText("번역할 내용을 입력하세요...")
        self.input_edit.setStyleSheet("QTextEdit { background-color: #1E1E1E; color: #FFFFFF; border: 1px solid #555555; border-radius: 6px; padding: 6px; font-family: 'Malgun Gothic'; font-size: 13px; }")
        frame_layout.addWidget(self.input_edit)
        
        control_layout = QHBoxLayout()
        self.lang_combo = QComboBox(self)
        for name, code in LANGUAGES:
            self.lang_combo.addItem(name, code)
        self.lang_combo.setStyleSheet("QComboBox { background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #555555; border-radius: 4px; padding: 3px 5px; font-family: 'Malgun Gothic'; font-size: 12px; } QComboBox QAbstractItemView { background-color: #2D2D2D; color: #FFFFFF; selection-background-color: #4A4A4A; }")
        control_layout.addWidget(self.lang_combo)
        
        self.btn_trans = QPushButton("번역하기", self)
        self.btn_trans.setFixedHeight(26)
        self.btn_trans.setStyleSheet("QPushButton { color: #FFFFFF; background-color: #0080FF; font-family: 'Malgun Gothic'; font-weight: bold; font-size: 12px; border: none; border-radius: 4px; padding: 0px 15px; } QPushButton:hover { background-color: #1A90FF; }")
        self.btn_trans.clicked.connect(self.execute_translation)
        control_layout.addWidget(self.btn_trans)
        frame_layout.addLayout(control_layout)
        
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #555555; background-color: #1A1A1A; border-top-left-radius: 6px; border-top-right-radius: 6px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; margin-top: 5px; }")
        
        self.result_label = QLabel("번역 결과가 여기에 표시됩니다.", self)
        self.result_label.setStyleSheet("QLabel { color: #00FFCC; font-size: 13px; font-family: 'Malgun Gothic'; padding: 6px; background: transparent; border: none; }")
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.scroll_area.setWidget(self.result_label)
        frame_layout.addWidget(self.scroll_area)
        
        manual_bottom_layout = QHBoxLayout()
        manual_bottom_layout.setContentsMargins(0, 0, 0, 0)
        manual_bottom_layout.setSpacing(0)
        
        self.btn_manual_copy = QPushButton("📋 결과 복사", self)
        self.btn_manual_copy.setFixedHeight(24)
        self.btn_manual_copy.setStyleSheet("QPushButton { color: #DDDDDD; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: rgba(255, 255, 255, 15); border-left: 1px solid #555555; border-bottom: 1px solid #555555; border-right: 1px solid #555555; border-top: none; border-bottom-left-radius: 6px; border-bottom-right-radius: 0px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(255, 255, 255, 35); }")
        self.btn_manual_copy.clicked.connect(self.copy_manual_text)
        manual_bottom_layout.addWidget(self.btn_manual_copy, 1)
        
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: rgba(255, 255, 255, 40); border-right: 1px solid #555555; border-bottom: 1px solid #555555; border-bottom-right-radius: 6px; }")
        self.sizegrip.setFixedSize(14, 24)
        manual_bottom_layout.addWidget(self.sizegrip, 0, Qt.AlignRight | Qt.AlignBottom)
        
        frame_layout.addLayout(manual_bottom_layout)
        self.bg_frame.setLayout(frame_layout)
        main_layout.addWidget(self.bg_frame)
        self.setLayout(main_layout)
        self.resize(360, 340)

    def execute_translation(self):
        text_to_translate = self.input_edit.toPlainText().strip()
        if not text_to_translate:
            self.result_label.setText("⚠️ 입력된 텍스트가 없습니다.")
            self.manual_result_pure = ""
            return
        
        target_code = self.lang_combo.currentData()
        self.result_label.setText("⏳ 번역 중...")
        
        self.trans_thread = TranslationThread(text_to_translate, 'auto', target_code)
        self.trans_thread.finished_signal.connect(self.on_translation_success)
        self.trans_thread.error_signal.connect(self.on_translation_failure)
        self.trans_thread.start()

    def on_translation_success(self, original, result):
        self.result_label.setText(result)
        self.manual_result_pure = result

    def on_translation_failure(self, error_msg):
        self.result_label.setText(error_msg)
        self.manual_result_pure = ""

    def copy_manual_text(self):
        if self.manual_result_pure:
            self.main_window.last_text = self.manual_result_pure
            pyperclip.copy(self.manual_result_pure)
            self.btn_manual_copy.setText("✅ 복사 완료!")
            QTimer.singleShot(1000, lambda: self.btn_manual_copy.setText("📋 결과 복사"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moving = True
            self.offset = event.pos()
    def mouseMoveEvent(self, event):
        if self.moving and event.buttons() == Qt.LeftButton: self.move(event.globalPos() - self.offset)
    def mouseReleaseEvent(self, event): self.moving = False


class MovableResizableTranslator(QWidget):
    drag_completed_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.source_lang = 'auto'
        self.target_lang = 'ko'
        self.last_text = ""
        
        self.current_ocr_source = ""
        self.current_ocr_translated = ""
        self.translated_result_pure = "" 
        
        self.auto_translate_on = True 
        self.drag_translate_on = False
        self.auto_popup_on = True     
        
        self.is_dragging_mouse = False
        self.drag_start_pos = None
        self.moving = False
        self.offset = QPoint()
        
        self.trans_thread = None
        self.is_translating = False 
        
        self.pixmap = QPixmap(resource_path("trans.ico"))
        self.initUI()
        
        self.manual_window = ManualTranslatorWindow(self.pixmap, self)
        self.create_tray_icon()
        
        self.drag_completed_signal.connect(self.trigger_drag_copy)
        mouse.hook(self.on_mouse_event)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_translation_triggers)
        self.timer.start(400)

    def initUI(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_frame = QFrame(self)
        self.bg_frame.setStyleSheet("QFrame { background-color: rgba(30, 30, 30, 225); border: 2px solid #555555; border-radius: 12px; }")
        
        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(15, 10, 15, 5)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        
        self.title_icon = QLabel(self)
        if not self.pixmap.isNull():
            self.title_icon.setPixmap(self.pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.title_icon.setText("🌐")
        title_layout.addWidget(self.title_icon)
        
        self.title_text = QLabel("ClipTrans", self)
        self.title_text.setStyleSheet("QLabel { color: #BBBBBB; font-size: 12px; font-family: 'Segoe UI', 'Malgun Gothic'; font-weight: bold; background: transparent; border: none; }")
        title_layout.addWidget(self.title_text)
        
        title_layout.addStretch()
        
        self.btn_view_source = QPushButton("📄 원문 보기", self)
        self.btn_view_source.setFixedSize(85, 22)
        self.btn_view_source.setStyleSheet("QPushButton { color: #55ffcc; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: rgba(0, 255, 204, 20); border: 1px solid #00ffcc; border-radius: 4px; } QPushButton:hover { background-color: rgba(0, 255, 204, 50); }")
        self.btn_view_source.setVisible(False)
        self.btn_view_source.clicked.connect(self.show_source_text)
        title_layout.addWidget(self.btn_view_source)
        
        self.btn_view_trans = QPushButton("🌐 번역 보기", self)
        self.btn_view_trans.setFixedSize(85, 22)
        self.btn_view_trans.setStyleSheet("QPushButton { color: #ffffff; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: #0080ff; border: none; border-radius: 4px; } QPushButton:hover { background-color: #1a90ff; }")
        self.btn_view_trans.setVisible(False)
        self.btn_view_trans.clicked.connect(self.show_translated_text)
        title_layout.addWidget(self.btn_view_trans)
        
        title_layout.addStretch()
        
        self.btn_settings = QPushButton("⚙️", self)
        self.btn_settings.setFixedSize(28, 22)
        self.btn_settings.setStyleSheet("QPushButton { color: #AAAAAA; font-size: 14px; background-color: transparent; border: none; border-radius: 4px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(255, 255, 255, 30); }")
        self.btn_settings.clicked.connect(self.show_settings_menu)
        title_layout.addWidget(self.btn_settings)
        
        self.btn_minimize = QPushButton("-", self)
        self.btn_minimize.setFixedSize(28, 22)
        self.btn_minimize.setStyleSheet("QPushButton { color: #AAAAAA; font-size: 16px; font-weight: bold; background-color: transparent; border: none; border-radius: 4px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(255, 255, 255, 30); }")
        self.btn_minimize.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.btn_minimize)
        
        self.btn_close = QPushButton("×", self)
        self.btn_close.setFixedSize(28, 22)
        self.btn_close.setStyleSheet("QPushButton { color: #AAAAAA; font-size: 16px; font-weight: bold; background-color: transparent; border: none; border-radius: 4px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(240, 71, 71, 200); }")
        self.btn_close.clicked.connect(QApplication.instance().quit) 
        title_layout.addWidget(self.btn_close)
        frame_layout.addLayout(title_layout)
        
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; margin-top: 8px; } QScrollBar:vertical { border: none; background: rgba(0, 0, 0, 50); width: 8px; border-radius: 4px; } QScrollBar::handle:vertical { background: rgba(255, 255, 255, 60); min-height: 20px; border-radius: 4px; }")
        
        self.label = QLabel("📢 글자를 복사(Ctrl+C)하거나 마우스로 드래그하면 번역이 실행됩니다.\n\n✏️ 수동 번역 버튼을 누르면 직접 텍스트를 타이핑하여 번역할 수 있습니다.", self)
        self.label.setStyleSheet("QLabel { color: #FFFFFF !important; font-size: 14px; font-family: 'Malgun Gothic'; font-weight: bold; background: transparent; border: none; }")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setWordWrap(True)
        self.scroll_area.setWidget(self.label)
        frame_layout.addWidget(self.scroll_area)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        bottom_layout.setSpacing(6)
        
        self.btn_manual = QPushButton("✏️ 수동 번역", self)
        self.btn_manual.setFixedSize(90, 24)
        self.btn_manual.setStyleSheet("QPushButton { color: #DDDDDD; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: rgba(0, 128, 255, 40); border: 1px solid #0080FF; border-radius: 4px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(0, 128, 255, 80); }")
        self.btn_manual.clicked.connect(self.open_manual_window)
        bottom_layout.addWidget(self.btn_manual)
        
        bottom_layout.addStretch() 
        
        self.btn_copy = QPushButton("📋 결과 복사", self)
        self.btn_copy.setFixedSize(90, 24)
        self.btn_copy.setStyleSheet("QPushButton { color: #DDDDDD; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: rgba(255, 255, 255, 20); border: 1px solid #777777; border-radius: 4px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(255, 255, 255, 45); }")
        self.btn_copy.clicked.connect(self.copy_translated_text)
        bottom_layout.addWidget(self.btn_copy)
        
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("background-color: rgba(255, 255, 255, 40); border-radius: 3px;")
        self.sizegrip.setFixedSize(14, 14)
        bottom_layout.addWidget(self.sizegrip, 0, Qt.AlignRight | Qt.AlignBottom)
        frame_layout.addLayout(bottom_layout)
        
        self.bg_frame.setLayout(frame_layout)
        main_layout.addWidget(self.bg_frame)
        self.setLayout(main_layout)

        self.resize(460, 220) 
        screen_geo = QApplication.primaryScreen().geometry()
        self.move(screen_geo.width() - self.width() - 30, screen_geo.height() - self.height() - 100)
        self.show()

    def show_source_text(self):
        display_text = f"[📄 감지 원문]\n\n{self.current_ocr_source}"
        self.label.setText(display_text)
        self.translated_result_pure = self.current_ocr_source
        self.btn_copy.setText("📋 원문 복사")
        self.btn_view_source.setStyleSheet("QPushButton { color: #ffffff; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: #00ffcc; color: #1e1e1e; border: none; border-radius: 4px; }")
        self.btn_view_trans.setStyleSheet("QPushButton { color: #ffffff; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: rgba(255, 255, 255, 15); border: 1px solid #777777; border-radius: 4px; }")

    def show_translated_text(self):
        display_text = f"[🌐 번역 결과 - {self.target_lang.upper()}]\n\n{self.current_ocr_translated}"
        self.label.setText(display_text)
        self.translated_result_pure = self.current_ocr_translated
        self.btn_copy.setText("📋 결과 복사")
        self.btn_view_source.setStyleSheet("QPushButton { color: #55ffcc; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: rgba(0, 255, 204, 20); border: 1px solid #00ffcc; border-radius: 4px; }")
        self.btn_view_trans.setStyleSheet("QPushButton { color: #ffffff; font-size: 11px; font-family: 'Malgun Gothic'; font-weight: bold; background-color: #0080ff; border: none; border-radius: 4px; }")

    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path("trans.ico")))
        self.tray_icon.setToolTip("ClipTrans")
        
        tray_menu = QMenu()
        tray_menu.setStyleSheet("QMenu { background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #555555; font-family: 'Malgun Gothic'; font-size: 13px; } QMenu::item { padding: 6px 25px 6px 20px; } QMenu::item:selected { background-color: #4A4A4A; }")
        
        show_action = QAction("🌐 번역 메인창 열기", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        manual_action = QAction("✏️ 수동 번역창 열기", self)
        manual_action.triggered.connect(self.open_manual_window_from_tray)
        tray_menu.addAction(manual_action)
        
        tray_menu.addSeparator()
        exit_action = QAction("❌ 프로그램 종료", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def open_manual_window_from_tray(self):
        screen_geo = QApplication.primaryScreen().geometry()
        self.manual_window.move(screen_geo.width() - self.manual_window.width() - 40, screen_geo.height() - self.manual_window.height() - 120)
        self.manual_window.show()
        self.manual_window.raise_()
        self.manual_window.activateWindow()

    def open_manual_window(self):
        self.manual_window.move(self.x() - self.manual_window.width() - 10, self.y())
        self.manual_window.show()
        self.manual_window.raise_()
        self.manual_window.activateWindow()

    def contextMenuEvent(self, event):
        menu = self.get_settings_menu_object()
        menu.exec_(event.globalPos())

    def get_settings_menu_object(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #555555; font-family: 'Malgun Gothic'; font-size: 13px; } QMenu::item { padding: 6px 25px 6px 20px; } QMenu::item:selected { background-color: #4A4A4A; } QMenu::item:checked { font-weight: bold; color: #00FFCC; }")
        
        action_auto_trans = QAction("📋 클립보드 번역 모드 활성화", self)
        action_auto_trans.setCheckable(True)
        action_auto_trans.setChecked(self.auto_translate_on)
        action_auto_trans.triggered.connect(self.toggle_auto_translate)
        menu.addAction(action_auto_trans)

        action_drag_trans = QAction("🖱️ 드래그 영역 번역 모드 활성화", self)
        action_drag_trans.setCheckable(True)
        action_drag_trans.setChecked(self.drag_translate_on)
        action_drag_trans.triggered.connect(self.toggle_drag_translate)
        menu.addAction(action_drag_trans)

        menu.addSeparator()
        action_popup = QAction("📱 감지시 창 자동생성", self)
        action_popup.setCheckable(True)
        action_popup.setChecked(self.auto_popup_on)
        action_popup.triggered.connect(self.toggle_auto_popup)
        menu.addAction(action_popup)
        
        menu.addSeparator()
        lang_menu = QMenu("🌐 번역할 언어 설정", menu)
        lang_menu.setStyleSheet(menu.styleSheet())
        for name, code in LANGUAGES:
            lang_action = QAction(name, self)
            lang_action.setCheckable(True)
            lang_action.setChecked(self.target_lang == code)
            lang_action.triggered.connect(lambda checked, c=code: self.change_target_lang(c))
            lang_menu.addAction(lang_action)
        menu.addMenu(lang_menu)
        
        menu.addSeparator()
        action_hide = QAction("📥 백그라운드로 숨기기", self)
        action_hide.triggered.connect(self.hide_to_background)
        menu.addAction(action_hide)
        
        return menu

    def show_settings_menu(self):
        menu = self.get_settings_menu_object()
        menu.exec_(self.btn_settings.mapToGlobal(QPoint(0, self.btn_settings.height())))

    def toggle_auto_translate(self, checked): 
        self.auto_translate_on = checked
        if checked:
            self.drag_translate_on = False
            self.label.setText("📋 실시간 클립보드(Ctrl+C) 감지 번역 모드가 가동 중입니다.")

    def toggle_drag_translate(self, checked):
        self.drag_translate_on = checked
        if checked:
            self.auto_translate_on = False
            self.label.setText("🖱️ 드래그 영역 자동 감지 번역 모드가 가동 중입니다. (글자를 마우스로 긁어보세요)")

    def toggle_auto_popup(self, checked): self.auto_popup_on = checked

    def change_target_lang(self, lang_code):
        self.target_lang = lang_code
        self.label.setText(f"🌐 번역 언어가 [{self.target_lang.upper()}] 버전으로 변경되었습니다.")

    def hide_to_background(self):
        self.hide()
        self.tray_icon.showMessage("ClipTrans", "백그라운드로 숨었습니다.", QSystemTrayIcon.Information, 1200)

    def copy_translated_text(self):
        if self.translated_result_pure:
            self.last_text = self.translated_result_pure
            pyperclip.copy(self.translated_result_pure)
            orig_text = self.btn_copy.text()
            self.btn_copy.setText("✅ 복사 완료!")
            QTimer.singleShot(1000, lambda: self.btn_copy.setText(orig_text))

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick: self.show_window()

    def show_window(self):
        if self.isHidden():
            self.showNormal()
            self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moving = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.moving and event.buttons() == Qt.LeftButton: self.move(event.globalPos() - self.offset)
    def mouseReleaseEvent(self, event): self.moving = False

    def on_mouse_event(self, event):
        if not self.drag_translate_on:
            return
        if self.isActiveWindow() or (self.manual_window and self.manual_window.isActiveWindow()):
            return

        if isinstance(event, mouse.ButtonEvent):
            if event.button == 'left':
                if event.event_type == 'down':
                    self.is_dragging_mouse = True
                    self.drag_start_pos = mouse.get_position()
                elif event.event_type == 'up' and self.is_dragging_mouse:
                    self.is_dragging_mouse = False
                    if self.drag_start_pos:
                        end_pos = mouse.get_position()
                        dist = ((end_pos[0] - self.drag_start_pos[0])**2 + (end_pos[1] - self.drag_start_pos[1])**2)**0.5
                        if dist > 15:
                            self.drag_completed_signal.emit()

    def trigger_drag_copy(self):
        if self.is_translating:
            return
        try:
            import keyboard
            old_clipboard = pyperclip.paste()
            keyboard.send('ctrl+c')
            
            QTimer.singleShot(80, lambda: self.process_translation(old_clipboard, is_drag=True))
        except Exception:
            pass

    def check_translation_triggers(self):
        if self.auto_translate_on and not self.is_translating:
            self.process_translation(None, is_drag=False)

    def process_translation(self, old_clipboard_data=None, is_drag=False):
        try:
            current_text = pyperclip.paste()
            if not current_text:
                return
            
            current_text = current_text.strip()
            
            if current_text and current_text != self.last_text:
                self.last_text = current_text
                self.is_translating = True 
                
                self.label.setText("⏳ 번역 요청 중...")
                self.btn_view_source.setVisible(False)
                self.btn_view_trans.setVisible(False)
                
                self.trans_thread = TranslationThread(current_text, self.source_lang, self.target_lang)
                
                self.trans_thread.finished_signal.connect(
                    lambda orig, res, d=is_drag: self.on_async_translation_success(orig, res, d)
                )
                self.trans_thread.error_signal.connect(self.on_async_translation_failure)
                
                self.trans_thread.finished.connect(self.reset_translating_status)
                self.trans_thread.start()
                
            if is_drag and old_clipboard_data is not None:
                pyperclip.copy(old_clipboard_data)
                
        except Exception:
            self.is_translating = False

    def on_async_translation_success(self, original, result, is_drag):
        self.current_ocr_source = original
        self.current_ocr_translated = result
        self.translated_result_pure = result 
        
        prefix = "🖱️ 드래그 영역" if is_drag else "📋 클립보드"
        display_text = f"[{prefix} 번역 결과 - {self.target_lang.upper()}]\n\n{result}"
        self.label.setText(display_text)
        self.scroll_area.verticalScrollBar().setValue(0)
        
        self.btn_view_source.setVisible(True)
        self.btn_view_trans.setVisible(True)
        self.show_translated_text()
        
        if self.auto_popup_on: 
            self.show_window()

    def on_async_translation_failure(self, error_msg):
        self.label.setText(error_msg)

    def reset_translating_status(self):
        """ 번역 스레드가 종료되면 상태를 초기화하여 다음 번역을 즉시 받을 수 있게 합니다. """
        self.is_translating = False

    def closeEvent(self, event):
        mouse.unhook_all()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)
    ex = MovableResizableTranslator()
    sys.exit(app.exec_())
