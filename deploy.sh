#!/bin/bash

set -e

PROJECT_DIR="/home/ubuntu/courtauction_crawler"
ENV_DIR="$PROJECT_DIR/env"
SERVICE_NAME="courtauction-crawler"

echo "🚀 Court Auction Crawler (Conda) 배포 시작..."

# 1. 프로젝트 디렉토리 이동
cd "$PROJECT_DIR" || exit 1

# 2. conda 초기화 (miniforge3 위치)
echo "🔧 conda 로드 중..."
source /home/ubuntu/miniforge3/etc/profile.d/conda.sh

# 3. conda 환경 생성 (없으면 생성)
if [ ! -d "$ENV_DIR" ]; then
    echo "📦 conda 환경 생성 중 (Python 3.12)..."
    conda create -y -p "$ENV_DIR" python=3.12
else
    echo "🔁 기존 conda 환경 사용"
fi

# 4. conda 환경 활성화
echo "🔧 conda 환경 활성화"
conda activate "$ENV_DIR"

# 5. 의존성 설치
echo "📦 requirements 설치 중..."
pip install --no-user -r requirements.txt

# 6. systemd 서비스 파일 복사
echo "⚙️  systemd 서비스 적용 중..."
sudo cp "$PROJECT_DIR/courtauction-crawler.service" /etc/systemd/system/

# 7. 데몬 리로드
sudo systemctl daemon-reload

# 8. 서비스 재시작
echo "🔄 서비스 재시작..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# 9. 상태 확인
sleep 2
sudo systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ 배포 완료!"
echo "📋 유용한 명령어:"
echo "  - 상태: sudo systemctl status $SERVICE_NAME"
echo "  - 로그: sudo journalctl -u $SERVICE_NAME -f"
echo "  - 재시작: sudo systemctl restart $SERVICE_NAME"
echo "  - 중지: sudo systemctl stop $SERVICE_NAME"
