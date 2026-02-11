"""
===================================================================================
Executive Exchange Monitor (임원용 환율 모니터)
===================================================================================
목적: 임원들이 한눈에 환율을 확인할 수 있는 고급 GUI 프로그램
대상: Python 초보자도 쉽게 이해하고 수정할 수 있도록 설계됨
===================================================================================
"""

import sys
import os
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu, QAction
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap


# ===================================================================================
# [리소스 경로 헬퍼 함수]
# ===================================================================================
# PyInstaller로 빌드된 .exe 파일에서 리소스 파일을 찾기 위한 함수
# ===================================================================================

def resource_path(relative_path):
    """
    PyInstaller로 빌드된 .exe에서 리소스 파일의 절대 경로를 반환합니다.
    
    Args:
        relative_path (str): 리소스 파일의 상대 경로
    
    Returns:
        str: 리소스 파일의 절대 경로
    """
    try:
        # PyInstaller가 생성한 임시 폴더 경로
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python 스크립트로 실행 시 현재 디렉토리 사용
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


# ===================================================================================
# [중요] 통화 설정 (CURRENCY_CONFIG)
# ===================================================================================
# 새로운 통화를 추가하려면 이 딕셔너리에 한 줄만 추가하면 됩니다!
# 형식: "표시할 이름": "야후 파이낸스 티커 심볼"
# 
# 예시:
# CURRENCY_CONFIG = {
#     "미국 USD": "KRW=X",        # 달러/원
#     "일본 JPY": "JPYKRW=X",     # 엔/원
#     "유럽 EUR": "EURKRW=X",     # 유로/원
# }
# 
# 현재는 USD/KRW만 표시하도록 설정되어 있습니다.
# ===================================================================================

CURRENCY_CONFIG = {
    "미국 USD": "KRW=X"  # 달러/원 환율
}


# ===================================================================================
# [클래스 1] 환율 데이터 가져오기 워커 (ExchangeDataWorker)
# ===================================================================================
# 이 클래스는 백그라운드에서 환율 데이터를 가져옵니다.
# QThread를 사용하면 UI가 멈추지 않고 부드럽게 작동합니다.
# ===================================================================================

class ExchangeDataWorker(QThread):
    """
    백그라운드 스레드로 환율 데이터를 가져오는 워커 클래스
    
    시그널 (Signals):
        - rate_updated: 환율 업데이트 성공 시 (가격, 변동폭) 전송
        - error_occurred: 에러 발생 시 에러 메시지 전송
    """
    
    # PyQt5 시그널 정의 (UI에 데이터를 전달하는 통로)
    rate_updated = pyqtSignal(float, float)  # (현재가격, 변동폭)
    error_occurred = pyqtSignal(str)         # 에러 메시지
    
    def __init__(self, ticker_symbol, parent=None):
        """
        워커 초기화
        
        Args:
            ticker_symbol (str): 야후 파이낸스 티커 심볼 (예: "KRW=X")
            parent: 부모 위젯 (선택사항)
        """
        super().__init__(parent)
        self.ticker_symbol = ticker_symbol  # 가져올 환율 심볼
        self.running = True                 # 스레드 실행 상태 플래그
    
    def run(self):
        """
        스레드 메인 루프
        60초마다 환율 데이터를 가져옵니다.
        """
        while self.running:
            try:
                # ===================================================================
                # [API 호출] 야후 파이낸스에서 환율 데이터 가져오기
                # ===================================================================
                # URL 구조:
                # - chart/{티커}: 특정 통화 쌍의 차트 데이터
                # - interval=1m: 1분 단위 데이터
                # - range=1d: 최근 1일 데이터
                # ===================================================================
                
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.ticker_symbol}?interval=1m&range=1d"
                
                # User-Agent 헤더를 추가해야 야후 파이낸스가 요청을 받아줍니다
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # HTTP GET 요청 보내기 (5초 타임아웃)
                response = requests.get(url, headers=headers, timeout=5)
                
                # ===================================================================
                # [데이터 파싱] JSON 응답에서 필요한 정보 추출
                # ===================================================================
                if response.status_code == 200:  # 요청 성공
                    data = response.json()  # JSON 문자열을 Python 딕셔너리로 변환
                    
                    # 데이터 구조: chart -> result -> [0] -> meta
                    result = data.get('chart', {}).get('result', [])
                    
                    if result:  # 데이터가 있으면
                        meta = result[0]['meta']
                        
                        # 현재 시장 가격
                        current_price = meta['regularMarketPrice']
                        
                        # 전일 종가
                        previous_close = meta['chartPreviousClose']
                        
                        # 변동폭 계산 (현재가 - 전일종가)
                        change = current_price - previous_close
                        
                        # UI에 데이터 전송 (시그널 발생)
                        self.rate_updated.emit(current_price, change)
                    else:
                        # 데이터가 비어있으면 에러 전송
                        self.error_occurred.emit("데이터 없음")
                else:
                    # HTTP 에러 (예: 404, 500 등)
                    self.error_occurred.emit(f"HTTP 오류 {response.status_code}")
            
            except requests.exceptions.Timeout:
                # 타임아웃 에러 (5초 안에 응답 없음)
                self.error_occurred.emit("연결 시간 초과")
            
            except requests.exceptions.ConnectionError:
                # 네트워크 연결 에러
                self.error_occurred.emit("네트워크 연결 실패")
            
            except Exception as e:
                # 기타 모든 에러
                self.error_occurred.emit("알 수 없는 오류")
                print(f"[디버그] 에러 상세: {e}")  # 개발자용 디버그 메시지
            
            # ===================================================================
            # [스마트 대기] 60초 대기 (0.5초씩 120번 체크)
            # ===================================================================
            # 한 번에 60초를 기다리면 프로그램 종료 시 60초를 기다려야 합니다.
            # 0.5초씩 나눠서 기다리면서 self.running을 체크하면
            # 프로그램 종료 시 즉시 루프를 빠져나갈 수 있습니다.
            # ===================================================================
            for _ in range(120):  # 120 × 0.5초 = 60초
                if not self.running:  # 종료 신호가 오면
                    break             # 즉시 루프 탈출
                self.msleep(500)      # 0.5초 대기
    
    def stop(self):
        """
        스레드를 안전하게 종료합니다.
        """
        self.running = False  # 루프 종료 플래그 설정
        self.wait()           # 스레드가 완전히 끝날 때까지 대기


# ===================================================================================
# [클래스 2] 메인 UI 위젯 (ExecutiveExchangeMonitor)
# ===================================================================================
# 임원용 환율 모니터의 메인 화면입니다.
# 깔끔하고 고급스러운 디자인으로 환율 정보를 표시합니다.
# ===================================================================================

class ExecutiveExchangeMonitor(QWidget):
    """
    임원용 환율 모니터 메인 위젯
    
    특징:
        - 테두리 없는 창 (Frameless)
        - 항상 위에 표시 (Always on Top)
        - 드래그로 이동 가능
        - 우클릭 메뉴로 종료
    """
    
    def __init__(self):
        """
        위젯 초기화
        """
        super().__init__()
        
        # 현재 표시 중인 통화 (CURRENCY_CONFIG의 첫 번째 항목)
        self.current_currency_name = list(CURRENCY_CONFIG.keys())[0]
        self.current_ticker = CURRENCY_CONFIG[self.current_currency_name]
        
        # 워커 스레드 (나중에 초기화)
        self.worker = None
        
        # UI 구성
        self.init_ui()
        
        # 환율 데이터 가져오기 시작
        self.start_worker()
    
    def init_ui(self):
        """
        UI 구성 (레이아웃, 라벨, 스타일 설정)
        """
        # ===================================================================
        # [윈도우 설정] 테두리 없고 항상 위에 표시되는 창
        # ===================================================================
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 윈도우 테두리 제거
            Qt.WindowStaysOnTopHint | # 항상 최상위에 표시
            Qt.Tool                   # 작업 표시줄에 표시 안 함
        )
        
        # 배경색 설정 (딥 차콜 - 고급스러운 다크 모드)
        self.setStyleSheet("background-color: #1E1E1E;")
        
        # 창 크기 및 위치
        self.resize(450, 250)
        self.move(200, 200)
        
        # ===================================================================
        # [레이아웃 구성] 수직 레이아웃 (위에서 아래로)
        # ===================================================================
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 30)  # 여백 (좌, 상, 우, 하)
        main_layout.setSpacing(20)  # 위젯 간 간격
        
        # -------------------------------------------------------------------
        # [1] 제목 라벨 (통화 이름) - 국기 이미지와 함께 표시
        # -------------------------------------------------------------------
        # 제목 섹션을 위한 수평 레이아웃 생성
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)  # 이미지와 텍스트 간격
        title_layout.setAlignment(Qt.AlignCenter)  # 중앙 정렬
        
        # 국기 이미지 라벨
        flag_label = QLabel()
        # resource_path() 함수를 사용하여 .exe에서도 이미지를 찾을 수 있도록 함
        flag_pixmap = QPixmap(resource_path("usa.png"))
        if not flag_pixmap.isNull():  # 이미지 로드 성공 시
            # 이미지 크기 조정 (높이 30px, 비율 유지)
            scaled_pixmap = flag_pixmap.scaledToHeight(30, Qt.SmoothTransformation)
            flag_label.setPixmap(scaled_pixmap)
        flag_label.setStyleSheet("background-color: transparent;")
        
        # 통화 이름 텍스트 라벨
        self.title_label = QLabel(self.current_currency_name)
        self.title_label.setStyleSheet("""
            color: #FFD700;              /* 골드 색상 (고급스러움) */
            font-size: 22px;             /* 크기 */
            font-weight: bold;           /* 굵게 */
            font-family: 'Malgun Gothic'; /* 한글 폰트 */
            background-color: transparent; /* 배경 투명 */
        """)
        
        # 수평 레이아웃에 국기와 텍스트 추가
        title_layout.addStretch()  # 왼쪽 여백
        title_layout.addWidget(flag_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()  # 오른쪽 여백
        
        # 메인 레이아웃에 제목 섹션 추가
        main_layout.addLayout(title_layout)
        
        # -------------------------------------------------------------------
        # [2] 구분선
        # -------------------------------------------------------------------
        separator = QLabel("─" * 40)
        separator.setStyleSheet("""
            color: #404040;
            font-size: 8px;
        """)
        separator.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(separator)
        
        # -------------------------------------------------------------------
        # [3] 환율 라벨 (매우 큰 숫자)
        # -------------------------------------------------------------------
        self.rate_label = QLabel("연결 중...")
        self.rate_label.setStyleSheet("""
            color: #FFFFFF;               /* 밝은 흰색 (가독성 최고) */
            font-size: 52px;              /* 매우 큰 크기 */
            font-weight: bold;            /* 굵게 */
            font-family: 'Malgun Gothic'; /* 한글 폰트 */
            background-color: transparent;
        """)
        self.rate_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.rate_label)
        
        # -------------------------------------------------------------------
        # [4] 변동폭 라벨 (▲/▼ 화살표와 숫자)
        # -------------------------------------------------------------------
        self.change_label = QLabel("―")
        self.change_label.setStyleSheet("""
            color: #AAAAAA;
            font-size: 20px;
            font-weight: bold;
            font-family: 'Malgun Gothic';
            background-color: transparent;
        """)
        self.change_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.change_label)
        
        # -------------------------------------------------------------------
        # [5] 하단 정보 (실시간 업데이트 안내)
        # -------------------------------------------------------------------
        footer_label = QLabel("실시간 환율 정보 • 60초마다 자동 업데이트")
        footer_label.setStyleSheet("""
            color: #666666;
            font-size: 11px;
            font-family: 'Malgun Gothic';
            background-color: transparent;
        """)
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)
        
        # 레이아웃 적용
        self.setLayout(main_layout)
    
    def start_worker(self):
        """
        환율 데이터를 가져오는 워커 스레드를 시작합니다.
        """
        # 기존 워커가 있으면 먼저 종료
        if self.worker:
            self.worker.stop()
        
        # UI를 초기 상태로 리셋
        self.rate_label.setText("연결 중...")
        self.change_label.setText("―")
        
        # 새 워커 생성 및 시작
        self.worker = ExchangeDataWorker(self.current_ticker)
        
        # 시그널 연결 (워커에서 UI로 데이터 전달)
        self.worker.rate_updated.connect(self.update_ui)      # 데이터 업데이트
        self.worker.error_occurred.connect(self.display_error) # 에러 표시
        
        # 워커 스레드 시작
        self.worker.start()
    
    def update_ui(self, price, change):
        """
        환율 데이터로 UI를 업데이트합니다.
        
        Args:
            price (float): 현재 환율
            change (float): 변동폭 (전일 대비)
        """
        # ===================================================================
        # [환율 표시] 천 단위 콤마 추가 (예: 1,450.00)
        # ===================================================================
        self.rate_label.setText(f"{price:,.2f}")
        
        # ===================================================================
        # [변동폭 표시] 상승/하락에 따라 색상 변경
        # ===================================================================
        if change > 0:
            # 상승: 빨간색 화살표
            self.change_label.setText(f"▲ {change:,.2f}")
            self.change_label.setStyleSheet("""
                color: #FF4444;               /* 빨간색 */
                font-size: 20px;
                font-weight: bold;
                font-family: 'Malgun Gothic';
                background-color: transparent;
            """)
        
        elif change < 0:
            # 하락: 파란색 화살표
            self.change_label.setText(f"▼ {abs(change):,.2f}")
            self.change_label.setStyleSheet("""
                color: #4444FF;               /* 파란색 */
                font-size: 20px;
                font-weight: bold;
                font-family: 'Malgun Gothic';
                background-color: transparent;
            """)
        
        else:
            # 변동 없음: 회색
            self.change_label.setText(f"― {abs(change):,.2f}")
            self.change_label.setStyleSheet("""
                color: #AAAAAA;               /* 회색 */
                font-size: 20px;
                font-weight: bold;
                font-family: 'Malgun Gothic';
                background-color: transparent;
            """)
    
    def display_error(self, error_message):
        """
        에러 메시지를 UI에 표시합니다.
        
        Args:
            error_message (str): 표시할 에러 메시지
        """
        self.rate_label.setText("오류")
        self.change_label.setText(error_message)
        self.change_label.setStyleSheet("""
            color: #FF9800;               /* 주황색 (경고) */
            font-size: 16px;
            font-family: 'Malgun Gothic';
            background-color: transparent;
        """)
    
    # ===========================================================================
    # [이벤트 핸들러] 마우스 및 메뉴 이벤트 처리
    # ===========================================================================
    
    def contextMenuEvent(self, event):
        """
        우클릭 시 컨텍스트 메뉴 표시
        """
        menu = QMenu(self)
        
        # 종료 메뉴 항목
        exit_action = QAction("종료 (Exit)", self)
        exit_action.triggered.connect(self.quit_app)
        
        menu.addAction(exit_action)
        
        # 메뉴 표시 (마우스 위치에)
        menu.exec_(self.mapToGlobal(event.pos()))
    
    def mousePressEvent(self, event):
        """
        마우스 클릭 시 (드래그 시작)
        """
        if event.button() == Qt.LeftButton:
            # 현재 마우스 위치 저장
            self.old_position = event.globalPos()
    
    def mouseMoveEvent(self, event):
        """
        마우스 드래그 중 (창 이동)
        """
        if event.buttons() == Qt.LeftButton:
            # 마우스 이동 거리 계산
            delta = QPoint(event.globalPos() - self.old_position)
            
            # 창 위치 업데이트
            self.move(self.x() + delta.x(), self.y() + delta.y())
            
            # 현재 위치 저장
            self.old_position = event.globalPos()
    
    def quit_app(self):
        """
        프로그램 종료 (워커 스레드 안전하게 종료)
        """
        if self.worker:
            self.worker.stop()  # 워커 스레드 종료
        
        QApplication.quit()  # 프로그램 종료
    
    def closeEvent(self, event):
        """
        창 닫기 이벤트 (X 버튼 클릭 시)
        """
        if self.worker:
            self.worker.stop()
        
        event.accept()  # 종료 승인


# ===================================================================================
# [메인 실행 코드]
# ===================================================================================
# 이 부분은 파일을 직접 실행할 때만 동작합니다.
# 다른 파일에서 import 할 때는 실행되지 않습니다.
# ===================================================================================

if __name__ == '__main__':
    # PyQt5 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 메인 위젯 생성 및 표시
    monitor = ExecutiveExchangeMonitor()
    monitor.show()
    
    # 이벤트 루프 시작 (프로그램 종료 시까지 실행)
    sys.exit(app.exec_())


# ===================================================================================
# [초보자를 위한 추가 설명]
# ===================================================================================
# 
# Q1: 새로운 통화를 추가하려면?
# A1: 파일 맨 위의 CURRENCY_CONFIG 딕셔너리에 한 줄 추가하세요.
#     예: "일본 JPY": "JPYKRW=X"
#     (현재 버전은 하나의 통화만 표시하지만, 구조는 확장 가능하게 설계됨)
# 
# Q2: 업데이트 주기를 변경하려면?
# A2: ExchangeDataWorker 클래스의 run() 메서드에서
#     for _ in range(120): 부분을 수정하세요.
#     예: 30초마다 업데이트 → range(60)
# 
# Q3: 창 크기를 변경하려면?
# A3: init_ui() 메서드의 self.resize(450, 250) 부분을 수정하세요.
# 
# Q4: 폰트 크기를 변경하려면?
# A4: 각 라벨의 setStyleSheet() 안의 font-size 값을 수정하세요.
# 
# Q5: 프로그램이 멈추면?
# A5: 네트워크 연결을 확인하고, 터미널에서 실행하여 에러 메시지를 확인하세요.
# 
# ===================================================================================
