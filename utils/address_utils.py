def build_full_address(item: dict) -> str:
    """매물 데이터에서 네이버 지도 검색용 전체 주소 생성"""

    # ---------------------------
    # 1) bgPlaceRdAllAddr (도로명 전체 주소)
    # ---------------------------
    addr1 = item.get("bgPlaceRdAllAddr")
    if addr1:
        return addr1.strip()

    # ---------------------------
    # 2) 도로명 주소 조합
    # rd1Nm + rd2Nm + rdEubMyun + rdNm + buldNo
    # ---------------------------
    rd1 = item.get("rd1Nm")
    rd2 = item.get("rd2Nm")
    rd3 = item.get("rdEubMyun")
    rd_nm = item.get("rdNm")
    buld_no = item.get("buldNo")

    if rd1 and rd2 and rd_nm and buld_no:
        road_addr = " ".join(
            part for part in [rd1, rd2, rd3, rd_nm, buld_no] if part
        ).strip()
        return road_addr

    # ---------------------------
    # 3) 지번주소 (구주소) 조합
    # hjguSido + hjguSigu + hjguDong + daepyoLotno
    # ---------------------------
    hj1 = item.get("hjguSido")
    hj2 = item.get("hjguSigu")
    hj3 = item.get("hjguDong")
    lotno = item.get("daepyoLotno")

    if hj1 and hj2 and hj3 and lotno:
        lot_addr = f"{hj1} {hj2} {hj3} {lotno}".strip()
        return lot_addr

    # ---------------------------
    # 4) 마지막 fallback → printSt
    # ---------------------------
    print_st = item.get("printSt")
    if print_st:
        return print_st.strip()

    # ---------------------------
    # 5) 최종 실패
    # ---------------------------
    return ""
