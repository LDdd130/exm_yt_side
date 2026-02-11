import sys
import requests
import json
import os
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QMenu, QSystemTrayIcon, QAction, qApp)
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QCursor

# ==========================================
# 1. 설정 관리자 (Config Manager)
#    - 사용자의 마지막 위치, 선택한 통화를 기억합니다.
# ==========================================
class ConfigManager:
    CONFIG_FILE = 'widget_config.json'
    DEFAULT_CONFIG = {
        "currency": "USD/KRW",
        "pos_x": 100,
        "pos_y": 100
    }

    @classmethod
    def load(cls):
        if not os.path.exists(cls.CONFIG_FILE):
            return cls.DEFAULT_CONFIG
        try:
            with open(cls.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return cls.DEFAULT_CONFIG

    @classmethod
    def save(cls, config_data):
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Config Save Failed: {e}")

# ==========================================
# 2. 데이터 워커 (Worker Thread)
#    - UI와 분리되어 백그라운드에서 데이터를 가져옵니다.
#    - Non-blocking Sleep을 구현하여 즉시 종료가 가능합니다.
# ==========================================
class ExchangeWorker(QThread):
    rate_updated = pyqtSignal(float, float, str, str) # price, change, pair, symbol
    error_occurred = pyqtSignal(str)

    # 지원 통화 및 야후 파이낸스 티커 매핑
    CURRENCY_MAP = {
        "USD/KRW": "KRW=X",
        "JPY/KRW": "JPYKRW=X",
        "BTC/USD": "BTC-USD",
        "ETH/USD": "ETH-USD"
    }

    def __init__(self, currency_pair, parent=None):
        super().__init__(parent)
        self.currency_pair = currency_pair
        self.running = True

    def run(self):
        ticker = self.CURRENCY_MAP.get(self.currency_pair)
        if not ticker:
            self.error_occurred.emit("Unsupported Pair")
            return

        while self.running:
            try:
                # 야후 파이낸스 비공식 API 사용 (상용화 시 유료 API 권장)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
                
                response = requests.get(url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0]['meta']
                        price = meta['regularMarketPrice']
                        prev_close = meta['chartPreviousClose']
                        change = price - prev_close
                        
                        # 성공 시 데이터 전송
                        self.rate_updated.emit(price, change, self.currency_pair, ticker)
                    else:
                        self.error_occurred.emit("Data Error")
                else:
                    self.error_occurred.emit(f"HTTP {response.status_code}")

            except Exception as e:
                self.error_occurred.emit("Network Error")

            # [핵심 개선] 좀비 프로세스 방지 (Smart Sleep)
            # 60초를 통으로 쉬지 않고, 0.5초마다 종료 신호(self.running)를 체크함
            # 앱 종료 시 즉시 루프를 탈출하여 스레드가 안전하게 종료됨
            for _ in range(120): 
                if not self.running: break
                self.msleep(500)

    def stop(self):
        self.running = False
        self.wait() # 스레드가 완전히 끝날 때까지 대기

# ==========================================
# 3. 메인 위젯 (Ghost Widget)
#    - 트레이 아이콘, 컨텍스트 메뉴, 드래그 이동 등을 담당
# ==========================================
class GhostExchangeWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # 설정 불러오기
        self.config = ConfigManager.load()
        self.current_pair = self.config.get("currency", "USD/KRW")
        
        self.worker = None
        self.tray_icon = None
        
        self.initUI()
        self.initTray()
        
        # 시작하자마자 워커 가동
        self.start_worker(self.current_pair)

    def initUI(self):
        # 윈도우 설정 (투명, 테두리 없음, 항상 위)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 마지막 저장된 위치로 이동
        self.move(self.config.get("pos_x", 100), self.config.get("pos_y", 100))
        
        # 레이아웃 구성
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 1. 타이틀 (통화 쌍)
        self.lbl_title = QLabel(self.current_pair)
        self.lbl_title.setStyleSheet("color: #AAAAAA; font-size: 12px; font-weight: bold;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)
        
        # 2. 환율 (메인 숫자)
        self.lbl_rate = QLabel("Connecting...")
        self.lbl_rate.setStyleSheet("color: white; font-size: 24px; font-weight: bold; font-family: 'Segoe UI';")
        self.lbl_rate.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_rate)
        
        # 3. 변동폭
        self.lbl_change = QLabel("-")
        self.lbl_change.setStyleSheet("color: white; font-size: 14px;")
        self.lbl_change.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_change)
        
        self.resize(220, 110)

    def initTray(self):
        # 시스템 트레이 아이콘 설정
        self.tray_icon = QSystemTrayIcon(self)
        
        # 기본 아이콘 사용 (실제 배포 시엔 QIcon('icon.png') 사용 권장)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        
        # 트레이 메뉴 구성
        tray_menu = QMenu()
        
        show_action = QAction("보이기 / 숨기기", self)
        show_action.triggered.connect(self.toggle_visibility)
        
        quit_action = QAction("완전 종료 (Quit)", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_click) # 더블클릭 이벤트 연결
        self.tray_icon.show()

    # --- Worker 관리 ---
    def start_worker(self, currency_pair):
        # 기존 워커가 돌고 있다면 정지
        if self.worker:
            self.worker.stop()
        
        # UI 초기화 상태로 변경
        self.lbl_rate.setText("Loading...")
        self.lbl_change.setText("-")
        self.lbl_title.setText(currency_pair)
        
        # 새 워커 시작
        self.worker = ExchangeWorker(currency_pair)
        self.worker.rate_updated.connect(self.update_ui)
        self.worker.error_occurred.connect(self.display_error)
        self.worker.start()

    def update_ui(self, price, change, pair, ticker):
        self.lbl_title.setText(pair)
        self.lbl_rate.setText(f"{price:,.2f}")
        
        # 색상 로직: 상승(빨강), 하락(파랑), 변동없음(흰색)
        if change > 0:
            self.lbl_change.setText(f"▲ {change:,.2f}")
            self.lbl_change.setStyleSheet("color: #FF5555; font-size: 14px; font-weight: bold;")
        elif change < 0:
            self.lbl_change.setText(f"▼ {abs(change):,.2f}")
            self.lbl_change.setStyleSheet("color: #5555FF; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_change.setText(f"- {abs(change):,.2f}")
            self.lbl_change.setStyleSheet("color: white; font-size: 14px;")
            
        # 트레이 아이콘에 마우스 올리면 현재 환율 툴팁 표시
        self.tray_icon.setToolTip(f"{pair}: {price:,.2f}")

    def display_error(self, msg):
        # 에러 발생 시 UI 처리
        self.lbl_rate.setText("Error")
        self.lbl_change.setText("Retrying...")
        self.lbl_change.setStyleSheet("color: orange; font-size: 12px;")

    # --- 이벤트 핸들러 ---
    def on_tray_click(self, reason):
        # 트레이 아이콘 더블클릭 시 창 보이기/숨기기 토글
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    # 우클릭 메뉴 (Context Menu)
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        # 1. 통화 선택 서브메뉴 (동적 생성)
        currency_menu = menu.addMenu("통화 선택 (Currency)")
        for pair in ExchangeWorker.CURRENCY_MAP.keys():
            action = QAction(pair, self)
            action.setCheckable(True)
            if pair == self.current_pair:
                action.setChecked(True)
            
            # Lambda 주의: 루프 내에서 클로저 변수 캡처 문제 해결을 위해 p=pair 사용
            action.triggered.connect(lambda checked, p=pair: self.change_currency(p))
            currency_menu.addAction(action)

        menu.addSeparator()
        
        # 2. 숨기기 & 종료
        hide_action = menu.addAction("숨기기 (Hide to Tray)")
        quit_action = menu.addAction("종료 (Quit)")
        
        action = menu.exec_(self.mapToGlobal(event.pos()))
        
        if action == quit_action:
            self.quit_app()
        elif action == hide_action:
            self.hide()
            self.tray_icon.showMessage("위젯 숨겨짐", "트레이 아이콘을 더블클릭하면 다시 열립니다.", QSystemTrayIcon.Information, 2000)

    def change_currency(self, new_pair):
        if new_pair == self.current_pair: return
        
        self.current_pair = new_pair
        self.start_worker(new_pair)
        
        # 변경 사항 즉시 저장
        self.config["currency"] = new_pair
        ConfigManager.save(self.config)

    # 창 드래그 이동 로직
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    # 앱 종료 처리
    def quit_app(self):
        # 종료 전 현재 위치 저장
        self.config["pos_x"] = self.x()
        self.config["pos_y"] = self.y()
        ConfigManager.save(self.config)
        
        # 워커 스레드 안전하게 종료
        if self.worker:
            self.worker.stop()
        qApp.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GhostExchangeWidget()
    ex.show()
    sys.exit(app.exec_())