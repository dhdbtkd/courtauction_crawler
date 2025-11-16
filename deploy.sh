#!/bin/bash

# Court Auction Crawler 배포 스크립트
# Oracle 인스턴스에서 실행

set -e

PROJECT_DIR="/home/ubuntu/courtauction_crawler"
SERVICE_NAME="courtauction-crawler"

echo "🚀 Court Auction Crawler 배포 시작..."

# 1. 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR" || exit 1

# 2. 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 가상환경 활성화됨"
fi

# 3. 의존성 설치
echo "📦 의존성 설치 중..."
pip3 install -r requirements.txt --user

# 4. systemd 서비스 파일 복사
echo "⚙️  systemd 서비스 설정 중..."
sudo cp "$PROJECT_DIR/courtauction-crawler.service" /etc/systemd/system/

# 5. systemd 데몬 리로드
sudo systemctl daemon-reload

# 6. 서비스 활성화 및 시작
echo "🔄 서비스 시작 중..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# 7. 서비스 상태 확인
sleep 2
sudo systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ 배포 완료!"
echo ""
echo "📋 유용한 명령어:"
echo "  - 서비스 상태 확인: sudo systemctl status $SERVICE_NAME"
echo "  - 서비스 로그 확인: sudo journalctl -u $SERVICE_NAME -f"
echo "  - 서비스 재시작: sudo systemctl restart $SERVICE_NAME"
echo "  - 서비스 중지: sudo systemctl stop $SERVICE_NAME"

