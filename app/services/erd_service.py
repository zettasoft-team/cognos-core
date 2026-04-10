"""
조인 관계 시트 데이터 → ERD 노드·엣지 생성
"""
from app.services.store import get_all_sheets


def build_erd_from_sheets(sheets: dict) -> dict:

    table_sheet  = sheets.get("table_list",    {})
    join_sheet   = sheets.get("join_relation", {})
    column_sheet = sheets.get("column_mapping",{})

    # 노드: 테이블명 → 컬럼 목록
    node_map: dict[str, list[str]] = {}
    for row in table_sheet.get("rows", []):
        table_name = row[0] if row else ""
        if table_name:
            node_map[table_name] = []

    for row in column_sheet.get("rows", []):
        if len(row) < 6:
            continue
        table, col_phys, _, _, pk, fk = row[:6]
        suffix = ""
        if pk == "Y" and fk == "Y":
            suffix = " (PK,FK)"
        elif pk == "Y":
            suffix = " (PK)"
        elif fk == "Y":
            suffix = " (FK)"
        if table in node_map:
            node_map[table].append(col_phys + suffix)

    nodes = [
        {"id": name, "label": name, "columns": cols}
        for name, cols in node_map.items()
    ]

    # 엣지
    edges = []
    for row in join_sheet.get("rows", []):
        if len(row) < 5:
            continue
        from_table, to_table, join_type, left_col, right_col = row[:5]
        edges.append({
            "from_": from_table,
            "to":    to_table,
            "label": f"{left_col} = {right_col}",
        })

    return {"nodes": nodes, "edges": edges}
