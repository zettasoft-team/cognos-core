"""
XML 시트 데이터 → ERD 렌더링용 JSON 변환
레퍼런스: HTML_ERD_Generator 기술 레퍼런스
"""


def build_erd_from_sheets(sheets: dict) -> dict:
    table_rows = sheets.get("table_list",     {}).get("rows", [])
    col_rows   = sheets.get("column_mapping", {}).get("rows", [])
    join_rows  = sheets.get("join_relation",  {}).get("rows", [])

    tables  = {}
    domains = []   # 순서 보존

    # ── 테이블 등록 ───────────────────────────────────────────────────────────
    for row in table_rows:
        logical, physical, folder, sql, status = (row + [""] * 5)[:5]
        d = folder or "기타"
        if d not in domains:
            domains.append(d)
        tables[logical] = {
            "domain":   d,
            "physical": physical,
            "cols":     [],
        }

    # ── 컬럼 추가 ─────────────────────────────────────────────────────────────
    for row in col_rows:
        logical, col_l, col_p, dtype, usage, pk, nullable = (row + [""] * 7)[:7]
        if logical not in tables:
            continue
        col = {"n": col_l, "t": dtype}
        if pk == "Y":
            col["pk"] = 1
        tables[logical]["cols"].append(col)

    # ── 관계 추출 ─────────────────────────────────────────────────────────────
    rels = []
    for row in join_rows:
        l_ref, r_ref, l_card, r_card = (row + [""] * 4)[:4]

        # [DatabaseView].[TABLE_NAME] → TABLE_NAME
        def extract(ref):
            return ref.split(".")[-1].strip("[]")

        l_name = extract(l_ref)
        r_name = extract(r_ref)

        # l_card 예: "one:one"  r_card 예: "one:many"
        l_max = l_card.split(":")[-1] if ":" in l_card else "one"
        r_max = r_card.split(":")[-1] if ":" in r_card else "many"

        # FK(many) → PK(one)
        # l이 one, r이 many → FK는 r(right) 쪽
        if r_max == "many":
            fk_tbl, pk_tbl = r_name, l_name
        else:
            # 둘 다 one → 1:1, FK는 보통 right 쪽으로 가정
            fk_tbl, pk_tbl = r_name, l_name

        rel_type = "1:1" if (l_max == "one" and r_max == "one") else "1:N"

        if fk_tbl in tables and pk_tbl in tables:
            rels.append({
                "f":    fk_tbl,   # FK 보유 (many)
                "t":    pk_tbl,   # PK 참조 (one)
                "type": rel_type,
            })

    return {
        "tables":  tables,
        "domains": domains,
        "rels":    rels,
    }
