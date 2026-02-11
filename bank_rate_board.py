import sys
import qtawesome as qta
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import QSize

class FlagApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()

        # 1. qtawesome으로 미국 국기 아이콘 가져오기
        # 'fa5s'는 FontAwesome 5 Solid 스타일을 의미합니다.
        icon = qta.icon('fa5s.flag-usa', color='#002868') # 미국 국기색 느낌의 남색
        
        icon_label = QLabel()
        # 아이콘 크기를 설정 (30x30)
        icon_label.setPixmap(icon.pixmap(QSize(30, 30)))

        # 2. 텍스트 레이블
        text_label = QLabel("USA", self)
        text_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        # 레이아웃에 추가
        layout.addWidget(icon_label)
        layout.addWidget(text_label)

        self.setLayout(layout)
        self.setWindowTitle('Icon Test')
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FlagApp()
    sys.exit(app.exec_())