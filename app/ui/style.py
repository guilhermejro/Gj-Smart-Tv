BG, CARD, BLUE, PURPLE, TEXT, MUTED = "#0E1016", "#1A1D29", "#4C7DFF", "#8B5CF6", "#E8EAF2", "#8A90A6"

QSS = f"""
* {{ font-family: 'Inter','Noto Sans','Ubuntu',sans-serif; font-size: 14px; color: {TEXT}; }}
QMainWindow, QWidget#page {{ background: {BG}; }}
QLabel#brand {{ font-size: 24px; font-weight: 800; color: {BLUE}; }}
QLabel#section {{ font-size: 17px; font-weight: 700; margin-top: 6px; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#error {{ color: #FF6B81; }}
QPushButton {{ background: {CARD}; border: 1px solid #2A2F45; border-radius: 10px; padding: 8px 16px; }}
QPushButton:hover {{ border-color: {BLUE}; }}
QPushButton:focus {{ border: 2px solid {BLUE}; }}
QPushButton:disabled {{ color: #555B70; }}
QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {BLUE}, stop:1 {PURPLE}); border: none; font-weight: 700; }}
QLineEdit, QComboBox {{ background: {CARD}; border: 1px solid #2A2F45; border-radius: 10px; padding: 8px 12px; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {BLUE}; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget#channels::item:selected {{ background: transparent; }}
QListWidget#chips::item {{ background: {CARD}; border-radius: 14px; padding: 6px 14px; margin: 3px; }}
QListWidget#chips::item:selected {{ background: {BLUE}; }}
QListWidget#side::item {{ padding: 8px 10px; border-radius: 8px; }}
QListWidget#side::item:selected {{ background: #262B40; border-left: 3px solid {BLUE}; }}
QTableWidget {{ background: {CARD}; border: 1px solid #2A2F45; border-radius: 10px; gridline-color: #2A2F45; }}
QHeaderView::section {{ background: #20243A; border: none; padding: 6px; }}
QProgressBar {{ background: #20243A; border: none; height: 4px; }}
QProgressBar::chunk {{ background: {BLUE}; }}
QSlider::groove:horizontal {{ height: 4px; background: #2A2F45; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {BLUE}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QScrollBar:horizontal, QScrollBar:vertical {{ background: transparent; width: 8px; height: 8px; }}
QScrollBar::handle {{ background: #2A2F45; border-radius: 4px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
"""
