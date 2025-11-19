import json
from datetime import datetime
from pathlib import Path
from config import settings


def debug_save_json(sido, sigu, raw_results):
    """디버그 모드일 때 크롤링 결과를 JSON 파일로 저장"""
    if not settings.DEBUG:
        return

    debug_dir = Path("./debug")
    debug_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = debug_dir / f"{timestamp}_{sido}_{sigu}.json"

    data = {"sido_code": sido, "sigu_code": sigu, "raw_results": raw_results}

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"💾 디버그 JSON 저장됨 → {filename}")
