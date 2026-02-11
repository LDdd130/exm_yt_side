## 환율 위젯 업그레이드 계획

### 1. 현재 코드 분석 및 문제점

**파일:** [`exchange_widget.py`](exchange_widget.py)

현재 `exchange_widget.py`는 단일 파일로 구성된 간단한 PyQt5 애플리케이션입니다. 주요 문제점은 다음과 같습니다.

*   **UI Freezing 위험:** `update_rate` 메서드 내에서 `requests.get`을 직접 호출하여 네트워크 요청이 메인 UI 스레드에서 처리됩니다. 네트워크 지연 발생 시 UI가 멈출 수 있습니다.
*   **단일 통화 지원:** 현재 USD/KRW 환율만 고정적으로 표시하며, 다른 통화를 볼 수 있는 기능이 없습니다.
*   **제한적인 종료 동작:** 창의 닫기(X) 버튼이나 우클릭 메뉴의 "종료"를 선택하면 애플리케이션이 즉시 종료됩니다. 시스템 트레이로 숨기는 기능이 없어 사용자 경험이 저하될 수 있습니다.
*   **설정 미저장:** 위젯의 위치나 마지막으로 선택한 통화 등 사용자 설정이 저장되지 않아, 애플리케이션 재시작 시 매번 초기 상태로 돌아갑니다.

### 2. 개선 방향 및 목표

사용자 요구 사항에 맞춰 애플리케이션을 상용 소프트웨어 수준으로 업그레이드하기 위한 개선 목표는 다음과 같습니다.

*   **UI 반응성 확보:** `QThread`를 활용하여 네트워크 요청을 백그라운드 스레드로 분리하여 UI Freezing을 방지합니다.
*   **확장 가능한 통화 관리:** 다중 통화(USD, JPY, BTC)를 지원하도록 구조를 개선하고, 사용자가 쉽게 통화를 전환할 수 있는 UI를 제공합니다.
*   **향상된 UX:** 시스템 트레이 기능을 구현하여 애플리케이션이 항상 작업 표시줄에 떠 있지 않고, 필요할 때만 복원될 수 있도록 합니다.
*   **개인화된 경험:** `config.json` 파일을 통해 사용자 설정을 영구적으로 저장하고 로드하여, 사용자별 맞춤 환경을 제공합니다.

### 3. 구현 계획 (TODO List)

이 모든 요구 사항을 처리하기 위한 단계별 구현 계획입니다.

```mermaid
graph TD
    A[시작] --> B{QThread를 이용한 비동기 API 호출}; 
    B --> C{다중 통화 지원 로직 구현}; 
    C --> D{시스템 트레이 기능 추가}; 
    D --> E{설정 저장 및 로드}; 
    E --> F[완료];

    subgraph QThread 구현
        B1[QThread 클래스 정의: `ExchangeWorker`] --> B2[시그널 정의: `rate_updated`, `error_occurred`];
        B2 --> B3[API 호출 로직을 `ExchangeWorker`의 `run` 메서드로 이동];
        B3 --> B4[메인 위젯에서 `ExchangeWorker` 인스턴스 생성 및 연결];
    end

    subgraph 다중 통화 지원
        C1[지원 통화 목록 정의] --> C2[우클릭 메뉴에 "통화 선택" 서브메뉴 추가];
        C2 --> C3[통화 선택 시 현재 통화 업데이트 로직 구현];
        C3 --> C4[UI 레이블 업데이트 로직 일반화];
    end

    subgraph 시스템 트레이
        D1[QSystemTrayIcon 인스턴스 생성] --> D2[트레이 아이콘 메뉴 정의: "표시", "종료"];
        D2 --> D3[창 닫기 이벤트 오버라이드: `closeEvent`];
        D3 --> D4[더블클릭 시 위젯 복원 로직 구현];
    end

    subgraph 설정 저장/로드
        E1[config.json 파일 경로 정의] --> E2[설정 저장 함수 `save_settings` 구현 (통화, 위치)];
        E2 --> E3[설정 로드 함수 `load_settings` 구현];
        E3 --> E4[애플리케이션 시작 시 `load_settings` 호출];
        E4 --> E5[위젯 이동 시 `save_settings` 호출];
        E5 --> E6[통화 선택 시 `save_settings` 호출];
    end

```

### TODO List

- [ ] `ExchangeWorker` QThread 클래스 정의 및 `rate_updated`, `error_occurred` 시그널 추가
- [ ] `update_rate`의 API 호출 로직을 `ExchangeWorker`의 `run` 메서드로 이동
- [ ] `GhostExchangeWidget`에서 `ExchangeWorker` 인스턴스 생성 및 시그널-슬롯 연결
- [ ] 지원 통화 목록 (USD, JPY, BTC) 정의 및 야후 파이낸스 티커 매핑
- [ ] 우클릭 `contextMenuEvent`에 "통화 선택" 서브메뉴 동적 생성
- [ ] 통화 선택 액션 시 `lbl_title` 및 `update_rate` 호출 인자 업데이트 로직 구현
- [ ] `QSystemTrayIcon` 인스턴스 생성 및 아이콘 설정
- [ ] 시스템 트레이 아이콘에 대한 `QMenu` (표시, 종료) 생성 및 연결
- [ ] `GhostExchangeWidget`의 `closeEvent` 오버라이드하여 창 숨기기 및 트레이 아이콘 표시
- [ ] 트레이 아이콘 더블클릭 시 위젯 복원 (`showNormal()`)
- [ ] `config.json` 파일에 위젯 위치 (x, y) 및 현재 통화 저장/로드 기능 구현 (`save_settings`, `load_settings`)
- [ ] 애플리케이션 시작 시 `load_settings`를 호출하여 이전 설정 적용
- [ ] 위젯 이동 (`mouseMoveEvent`) 및 통화 변경 시 `save_settings` 호출
- [ ] 기존 `update_rate` 메서드를 통화 인자를 받을 수 있도록 수정 및 일반화
- [ ] 야후 파이낸스 API에서 JPY 및 BTC 환율 데이터를 가져오는 로직 추가
- [ ] 에러 처리 및 사용자 피드백 개선
