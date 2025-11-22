from datetime import datetime


class NotificationService:
    """
    신규 매물 → 알림 규칙 확인 → 일치 시 Slack/Telegram 전송 + 로그 기록
    """

    def __init__(self, notif_repo, auction_repo, notifier):
        self.notif_repo = notif_repo
        self.auction_repo = auction_repo
        self.notifier = notifier

    async def process_new_auctions(self, new_auctions):
        rules = self.notif_repo.get_active_rules()
        print(f"🔎 활성 규칙 {len(rules)}개 확인 중...")

        for rule in rules:
            for auction in new_auctions:
                if not self._match_rule(rule, auction):
                    continue

                channels = self.notif_repo.get_channels_by_user(rule["user_id"])
                message = self._format_message(auction, rule)

                for ch in channels:
                    if not ch.get("enabled"):
                        continue
                    channel_type = ch["type"]

                    message = self._format_message(auction, rule, channel_type)
                    # 실제 메시지 전송
                    if channel_type == "slack":
                        await self.notifier.send_slack_message(
                            ch["identifier"], message
                        )
                    elif channel_type == "telegram":
                        # 썸네일 이미지를 함께 전송
                        await self.notifier.send_telegram_message(
                            ch["identifier"],
                            message,
                            image_url=auction.get("thumbnail_src"),
                        )

                    # 로그 기록
                    self.notif_repo.insert_notification_log(
                        {
                            "user_id": rule["user_id"],
                            "rule_id": rule["id"],
                            "auction_id": auction.get("id"),
                            "channel_id": ch["id"],
                            "message": message,
                            "sent_at": datetime.now().isoformat(),
                            "is_read": False,
                        }
                    )

                print(f"✅ 사용자 {rule['user_id']}에게 알림 전송 완료")

    # ---------------------------
    # 내부 로직 (필터 / 포맷)
    # ---------------------------

    def _match_rule(self, rule, auction):
        """규칙 조건 일치 확인"""

        # ✅ 카테고리 비교
        if rule.get("category") and rule["category"] != auction.get("category"):
            return False

        # ✅ 시도(sido) 코드 비교
        if rule.get("sido_code"):
            if int(rule["sido_code"]) != int(auction.get("sido_code", 0)):
                return False

        # ✅ 시군구(sigu) 코드 비교 (앞 2자리 시도코드 제외)
        if rule.get("sigu_code"):
            rule_sigu = str(rule["sigu_code"])
            auction_sigu = str(auction.get("sigu_code", "0"))
            rule_sigu_trimmed = rule_sigu[2:] if len(rule_sigu) > 2 else rule_sigu
            if rule_sigu_trimmed != auction_sigu:
                return False

        # ✅ 가격 범위 비교
        auction_price = float(auction.get("minimum_price") or 0)
        if rule.get("price_min") and auction_price < float(rule["price_min"]):
            return False
        if rule.get("price_max") and auction_price > float(rule["price_max"]):
            return False

        # ✅ 면적(area) 비교
        try:
            auction_area = float(auction.get("area") or 0)
        except ValueError:
            auction_area = 0

        if rule.get("area_min") and auction_area < float(rule["area_min"]):
            return False
        if rule.get("area_max") and auction_area > float(rule["area_max"]):
            return False

        # ✅ 키워드 비교
        if rule.get("keyword") and rule["keyword"] not in auction.get("address", ""):
            return False

        return True

    def _format_message(self, auction, rule, channel_type="telegram"):
        """메시지 내용 포맷"""

        title = (
            "📢 *새 매물 알림!*"
            if channel_type == "telegram"
            else ":rotating_light: *새 매물 알림!*"
        )

        # ----------------------------
        # 💰 금액 단위 변환 (만원 단위 이하 무시)
        # ----------------------------
        try:
            price = int(float(auction.get("minimum_price") or 0))
        except ValueError:
            price = 0

        if price >= 100_000_000:  # 억 단위 포함
            eok = price // 100_000_000
            man = (price % 100_000_000) // 10_000
            price_text = f"{eok}억 {man:,}만원" if man > 0 else f"{eok}억"
        elif price >= 10_000:  # 만원 단위만 있는 경우
            man = price // 10_000
            price_text = f"{man:,}만원"
        else:
            price_text = "가격 정보 없음"

        # ----------------------------
        # 📏 면적 / 기타 정보
        # ----------------------------
        area_text = (
            f"{auction.get('area')}㎡" if auction.get("area") else "면적 정보 없음"
        )
        date_text = auction.get("auction_date") or "미정"
        address = auction.get("address", "주소 정보 없음")
        category = auction.get("category", "분류 없음")

        # ----------------------------
        # 📱 채널별 메시지 포맷
        # ----------------------------
        if channel_type == "telegram":
            message = (
                f"{title}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🏷 *규칙:* {rule.get('name', '-')}\n"
                f"🏠 *종류:* {category}\n"
                f"📍 *주소:* {address}\n"
                f"📏 *면적:* {area_text}\n"
                f"💰 *최저가:* {price_text}\n"
                f"🗓 *매각기일:* {date_text}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔗 [매물 이미지 보기]({auction.get('thumbnail_src', '')})"
            )
        else:
            message = (
                f":rotating_light: *새 매물 알림!*\n"
                f"> *알림명:* {rule.get('name', '-')}\n"
                f"> *종류:* {category}\n"
                f"> *주소:* {address}\n"
                f"> *면적:* {area_text}\n"
                f"> *최저가:* {price_text}\n"
                f"> *매각기일:* {date_text}\n"
                f"> <{auction.get('thumbnail_src', '')}|이미지 보기>"
            )

        return message
