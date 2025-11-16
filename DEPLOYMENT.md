# Oracle 인스턴스 배포 가이드

## 개요

이 프로젝트는 FastAPI 기반의 법원경매 크롤러이며, 다음 기능을 포함합니다:

-   주기적 크롤링 (매주 월/목 오전 10시)
-   텔레그램 웹훅 서비스 (별도 실행 불필요)

## 사전 준비

1. **프로젝트 디렉토리 구조**

    ```
    /home/ubuntu/courtauction_crawler/
    ├── main.py
    ├── requirements.txt
    ├── courtauction-crawler.service
    └── ...
    ```

2. **환경 변수 설정**
    - `/home/ubuntu/scripts/.env` 파일에 다음 변수들이 설정되어 있어야 합니다:
        - `SUPABASE_URL`
        - `SUPABASE_KEY`
        - `SLACK_TOKEN`
        - `TELEGRAM_BOT_API_KEY`
        - `TELEGRAM_CHAT_ID`

## 배포 방법

### 방법 1: 배포 스크립트 사용 (권장)

```bash
# 1. 프로젝트 디렉토리로 이동
cd /home/ubuntu/courtauction_crawler

# 2. 배포 스크립트에 실행 권한 부여
chmod +x deploy.sh

# 3. 배포 스크립트 실행
./deploy.sh
```

### 방법 2: 수동 배포

```bash
# 1. 의존성 설치
cd /home/ubuntu/courtauction_crawler
pip3 install -r requirements.txt --user

# 2. systemd 서비스 파일 복사
sudo cp courtauction-crawler.service /etc/systemd/system/

# 3. systemd 데몬 리로드
sudo systemctl daemon-reload

# 4. 서비스 활성화 및 시작
sudo systemctl enable courtauction-crawler
sudo systemctl start courtauction-crawler
```

## 서비스 관리

### 서비스 상태 확인

```bash
sudo systemctl status courtauction-crawler
```

### 서비스 로그 확인

```bash
# 실시간 로그 확인
sudo journalctl -u courtauction-crawler -f

# 최근 100줄 로그 확인
sudo journalctl -u courtauction-crawler -n 100
```

### 서비스 재시작

```bash
sudo systemctl restart courtauction-crawler
```

### 서비스 중지

```bash
sudo systemctl stop courtauction-crawler
```

### 서비스 시작

```bash
sudo systemctl start courtauction-crawler
```

## 텔레그램 웹훅 설정

텔레그램 웹훅은 `main.py`에 포함되어 있어 별도로 실행할 필요가 없습니다.

웹훅 URL을 텔레그램에 등록하려면:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/"
```

## 크롤링 스케줄

-   **스케줄**: 매주 월요일, 목요일 오전 10시 (KST)
-   **시작 시**: 서비스 시작 시 즉시 크롤링 실행
-   **스케줄러**: APScheduler 사용

## 포트 설정

기본 포트는 `8000`입니다. 변경하려면 `courtauction-crawler.service` 파일의 `ExecStart` 부분을 수정하세요:

```ini
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 문제 해결

### 서비스가 시작되지 않는 경우

1. 로그 확인:

    ```bash
    sudo journalctl -u courtauction-crawler -n 50
    ```

2. Python 경로 확인:

    ```bash
    which python3
    ```

3. 의존성 확인:
    ```bash
    pip3 list | grep -E "fastapi|uvicorn|apscheduler"
    ```

### 포트가 이미 사용 중인 경우

다른 포트를 사용하거나 기존 프로세스를 종료:

```bash
# 포트 8000 사용 중인 프로세스 확인
sudo lsof -i :8000

# 프로세스 종료
sudo kill -9 <PID>
```

## 참고사항

-   서비스는 `ubuntu` 사용자로 실행됩니다. 다른 사용자를 사용하려면 `courtauction-crawler.service` 파일의 `User` 항목을 수정하세요.
-   로그는 systemd journal에 저장되며, `journalctl` 명령어로 확인할 수 있습니다.
-   서비스는 자동 재시작되도록 설정되어 있습니다 (Restart=always).
