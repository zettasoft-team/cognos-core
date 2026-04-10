"""
저장된 시트 데이터 → 트리 구조 변환
"""


def build_tree_from_sheets(sheets: dict) -> list:
    table_rows = sheets.get("table_list",     {}).get("rows", [])
    dim_rows   = sheets.get("dimension_view", {}).get("rows", [])
    join_rows  = sheets.get("join_relation",  {}).get("rows", [])
    fact_rows  = sheets.get("fact_calc",      {}).get("rows", [])
    col_rows   = sheets.get("column_mapping", {}).get("rows", [])

    tree = []

    # ── DatabaseView ──────────────────────────────────────────────
    db_node = {"id": "ns-DatabaseView", "type": "namespace", "label": "DatabaseView", "children": []}

    folders: dict[str, dict] = {}
    for row in table_rows:
        logical, physical, folder, sql, status = (row + [""] * 5)[:5]
        if folder not in folders:
            f_node = {"id": f"folder-{folder}", "type": "folder", "label": folder, "children": []}
            folders[folder] = f_node
            db_node["children"].append(f_node)

        # 해당 테이블의 컬럼 수집
        cols = [c for c in col_rows if c[0] == logical]
        col_children = [
            {
                "id":       f"col-{logical}-{c[1]}",
                "type":     "queryItem",
                "label":    c[1],
                "physical": c[2],
                "datatype": c[3],
                "usage":    c[4],
                "pk":       c[5] if len(c) > 5 else "N",
                "nullable": c[6] if len(c) > 6 else "Y",
                "children": [],
            }
            for c in cols
        ]

        qs_node = {
            "id":       f"qs-{logical}",
            "type":     "querySubject",
            "label":    logical,
            "physical": physical,
            "sql":      sql,
            "status":   status,
            "children": col_children,
        }
        folders[folder]["children"].append(qs_node)

    tree.append(db_node)

    # ── DimensionalView ───────────────────────────────────────────
    dim_node = {"id": "ns-DimensionalView", "type": "namespace", "label": "DimensionalView", "children": []}

    dim_map: dict[str, dict] = {}
    for row in dim_rows:
        dim_name, hier_name, lv_name, ref = (row + [""] * 4)[:4]
        if dim_name not in dim_map:
            d = {"id": f"dim-{dim_name}", "type": "dimension", "label": dim_name, "children": []}
            dim_map[dim_name] = d
            dim_node["children"].append(d)
        dim = dim_map[dim_name]

        hier = next((h for h in dim["children"] if h["label"] == hier_name), None)
        if hier is None:
            hier = {"id": f"hier-{dim_name}-{hier_name}", "type": "hierarchy", "label": hier_name, "children": []}
            dim["children"].append(hier)

        hier["children"].append({
            "id":       f"lv-{dim_name}-{hier_name}-{lv_name}",
            "type":     "level",
            "label":    lv_name,
            "refobj":   ref,
            "children": [],
        })

    # Fact measures
    if fact_rows:
        fact_folder = {"id": "folder-measures", "type": "folder", "label": "Measures", "children": []}
        for row in fact_rows:
            name, agg, dtype, expr = (row + [""] * 4)[:4]
            fact_folder["children"].append({
                "id":         f"measure-{name}",
                "type":       "measure",
                "label":      name,
                "aggregate":  agg,
                "datatype":   dtype,
                "expression": expr,
                "children":   [],
            })
        dim_node["children"].append(fact_folder)

    tree.append(dim_node)

    # ── Relationships ─────────────────────────────────────────────
    if join_rows:
        rel_node = {"id": "ns-relationships", "type": "namespace", "label": "Relationships", "children": []}
        for i, row in enumerate(join_rows):
            l_ref, r_ref, l_card, r_card = (row + [""] * 4)[:4]
            rel_node["children"].append({
                "id":       f"rel-{i}",
                "type":     "relationship",
                "label":    f"{l_ref.split('.')[-1].strip('[]')} ↔ {r_ref.split('.')[-1].strip('[]')}",
                "left":     l_ref,
                "right":    r_ref,
                "leftCard": l_card,
                "rightCard": r_card,
                "children": [],
            })
        tree.append(rel_node)

    return tree
