"""
Cognos Framework Manager XML 파서 / 재생성기
실제 BMT 스키마 (http://www.developer.cognos.com/schemas/bmt/60/5) 기반
"""
from lxml import etree
from pathlib import Path

NS  = "http://www.developer.cognos.com/schemas/bmt/60/5"
NSM = {"bmt": NS}


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def _text(el, child: str) -> str:
    r = el.find(_tag(child))
    return r.text.strip() if r is not None and r.text else ""


def _name(el) -> str:
    """<name locale="ko"> 또는 <name> 첫 번째 값 반환"""
    r = el.find(_tag("name"))
    return r.text.strip() if r is not None and r.text else ""


def _all_query_subjects(root: etree._Element) -> list[dict]:
    """DatabaseView 네임스페이스의 모든 querySubject 수집 (folder 포함)"""
    subjects = []
    db_ns = _find_namespace(root, "DatabaseView")
    if db_ns is None:
        return subjects

    for el in db_ns.iter(_tag("querySubject")):
        # 소속 폴더 찾기
        folder_name = _get_parent_folder_name(db_ns, el)
        sql_el = el.find(".//" + _tag("sql"))
        sql    = sql_el.text.strip() if sql_el is not None and sql_el.text else ""

        # PK 컬럼 목록 (determinants)
        pk_refs = set()
        for det in el.findall(".//" + _tag("determinant")):
            if _text(det, "identifiesRow") == "true":
                for ref in det.findall(".//" + _tag("refobj")):
                    if ref.text:
                        # [Subject].[column] 에서 column 부분 추출
                        parts = ref.text.strip().split(".")
                        pk_refs.add(parts[-1].strip("[]"))

        items = []
        for qi in el.findall(_tag("queryItem")):
            col_name = _name(qi)
            items.append({
                "name":        col_name,
                "externalName": _text(qi, "externalName"),
                "usage":       _text(qi, "usage"),
                "datatype":    _text(qi, "datatype"),
                "nullable":    _text(qi, "nullable"),
                "is_pk":       col_name in pk_refs,
            })

        subjects.append({
            "logical_name":   _name(el),
            "physical_name":  _text(el, "description"),
            "folder":         folder_name,
            "sql":            sql,
            "status":         el.get("status", ""),
            "items":          items,
        })
    return subjects


def _find_namespace(root: etree._Element, name: str):
    """이름으로 namespace 엘리먼트 탐색"""
    for ns in root.iter(_tag("namespace")):
        if _name(ns) == name:
            return ns
    return None


def _get_parent_folder_name(ns_el: etree._Element, target) -> str:
    """target 엘리먼트의 부모 folder 이름 반환"""
    for folder in ns_el.findall(_tag("folder")):
        for child in folder.iter(_tag("querySubject")):
            if child is target:
                return _name(folder)
    return ""


# ── 6개 시트 파싱 ────────────────────────────────────────────────────────────

def _parse_table_list(subjects: list[dict]) -> dict:
    cols = ["테이블명(논리)", "테이블명(물리)", "폴더", "SQL", "상태"]
    rows = [
        [s["logical_name"], s["physical_name"], s["folder"], s["sql"], s["status"]]
        for s in subjects
    ]
    return {"columns": cols, "rows": rows}


def _parse_column_mapping(subjects: list[dict]) -> dict:
    cols = ["테이블명(논리)", "컬럼명(논리)", "컬럼명(물리)", "데이터타입", "용도", "PK", "NULL허용"]
    rows = []
    for s in subjects:
        for item in s["items"]:
            rows.append([
                s["logical_name"],
                item["name"],
                item["externalName"],
                item["datatype"],
                item["usage"],
                "Y" if item["is_pk"] else "N",
                "N" if item["nullable"] == "false" else "Y",
            ])
    return {"columns": cols, "rows": rows}


def _parse_join_relation(root: etree._Element) -> dict:
    cols = ["Left 테이블", "Right 테이블", "Left 카디널리티", "Right 카디널리티", "Left mincard", "Right mincard"]
    rows = []
    for rel in root.iter(_tag("relationship")):
        left  = rel.find(_tag("left"))
        right = rel.find(_tag("right"))
        if left is None or right is None:
            continue
        l_ref  = _text(left,  "refobj")
        r_ref  = _text(right, "refobj")
        l_min  = _text(left,  "mincard")
        l_max  = _text(left,  "maxcard")
        r_min  = _text(right, "mincard")
        r_max  = _text(right, "maxcard")
        rows.append([l_ref, r_ref, f"{l_min}:{l_max}", f"{r_min}:{r_max}", l_min, r_min])
    return {"columns": cols, "rows": rows}


def _parse_dimension_view(root: etree._Element) -> dict:
    cols = ["차원명", "계층명", "레벨명", "참조 객체"]
    rows = []
    for dim in root.iter(_tag("dimension")):
        dim_name = _name(dim)
        for hier in dim.findall(_tag("hierarchy")):
            hier_name = _name(hier)
            for lv in hier.findall(_tag("level")):
                lv_name = _name(lv)
                ref_el  = lv.find(_tag("refobj"))
                ref     = ref_el.text.strip() if ref_el is not None and ref_el.text else ""
                rows.append([dim_name, hier_name, lv_name, ref])
    return {"columns": cols, "rows": rows}


def _parse_meaning_dict(subjects: list[dict]) -> dict:
    """
    identifier usage 컬럼을 NL2SQL 의미사전으로 활용
    (논리명 → 물리명 매핑)
    """
    cols = ["테이블명(논리)", "컬럼명(논리)", "컬럼명(물리)", "용도(usage)", "데이터타입", "비고"]
    rows = []
    for s in subjects:
        for item in s["items"]:
            if item["usage"] in ("identifier", "fact"):
                rows.append([
                    s["logical_name"],
                    item["name"],
                    item["externalName"],
                    item["usage"],
                    item["datatype"],
                    "",
                ])
    return {"columns": cols, "rows": rows}


def _parse_fact_calc(root: etree._Element) -> dict:
    cols = ["Measure명", "집계방식", "데이터타입", "표현식"]
    rows = []
    for m in root.iter(_tag("measure")):
        rows.append([
            _name(m),
            _text(m, "regularAggregate"),
            _text(m, "datatype"),
            _text(m, "expression"),
        ])
    return {"columns": cols, "rows": rows}


# ── Public API ───────────────────────────────────────────────────────────────

def parse_xml(xml_path: Path) -> dict[str, dict]:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    subjects = _all_query_subjects(root)

    return {
        "table_list":     _parse_table_list(subjects),
        "column_mapping": _parse_column_mapping(subjects),
        "join_relation":  _parse_join_relation(root),
        "dimension_view": _parse_dimension_view(root),
        "meaning_dict":   _parse_meaning_dict(subjects),
        "fact_calc":      _parse_fact_calc(root),
    }


# ── XML 재생성 ───────────────────────────────────────────────────────────────

def generate_xml(sheets: dict[str, dict]) -> bytes:
    root = etree.Element("project",
                         queryMode="dynamic",
                         nsmap={None: NS})

    _build_db_view(root, sheets)
    _build_relationships(root, sheets)
    _build_dim_view(root, sheets)

    return etree.tostring(root, pretty_print=True,
                          xml_declaration=True, encoding="UTF-8")


def _sub(parent, tag: str, text: str = None, **attrib):
    el = etree.SubElement(parent, _tag(tag), **attrib)
    if text is not None:
        el.text = text
    return el


def _build_db_view(root, sheets: dict):
    ns_el = _sub(root, "namespace")
    _sub(ns_el, "name", "DatabaseView")

    table_rows  = sheets.get("table_list",     {}).get("rows", [])
    col_rows    = sheets.get("column_mapping", {}).get("rows", [])

    for t_row in table_rows:
        logical, physical, folder, sql, status = (t_row + [""] * 5)[:5]
        qs = _sub(ns_el, "querySubject", status=status)
        _sub(qs, "name", logical)
        _sub(qs, "description", physical)
        defn = _sub(qs, "definition")
        dbq  = _sub(defn, "dbQuery")
        _sub(dbq, "sql", sql)

        for c_row in col_rows:
            if c_row[0] != logical:
                continue
            _, col_logical, col_physical, datatype, usage, pk, nullable = (c_row + [""] * 7)[:7]
            qi = _sub(qs, "queryItem")
            _sub(qi, "name", col_logical)
            _sub(qi, "externalName", col_physical)
            _sub(qi, "usage", usage)
            _sub(qi, "datatype", datatype)
            _sub(qi, "nullable", "false" if nullable == "N" else "true")


def _build_relationships(root, sheets: dict):
    for r_row in sheets.get("join_relation", {}).get("rows", []):
        if len(r_row) < 4:
            continue
        l_ref, r_ref, l_card, r_card = r_row[:4]
        l_min, l_max = (l_card.split(":") + ["", ""])[:2]
        r_min, r_max = (r_card.split(":") + ["", ""])[:2]
        rel = _sub(root, "relationship")
        left = _sub(rel, "left")
        _sub(left, "refobj", l_ref)
        _sub(left, "mincard", l_min)
        _sub(left, "maxcard", l_max)
        right = _sub(rel, "right")
        _sub(right, "refobj", r_ref)
        _sub(right, "mincard", r_min)
        _sub(right, "maxcard", r_max)


def _build_dim_view(root, sheets: dict):
    ns_el = _sub(root, "namespace")
    _sub(ns_el, "name", "DimensionalView")

    dims: dict[str, dict[str, list]] = {}
    for row in sheets.get("dimension_view", {}).get("rows", []):
        dim_name, hier_name, lv_name, ref = (row + [""] * 4)[:4]
        dims.setdefault(dim_name, {}).setdefault(hier_name, []).append((lv_name, ref))

    for dim_name, hiers in dims.items():
        dim_el = _sub(ns_el, "dimension")
        _sub(dim_el, "name", dim_name)
        for hier_name, levels in hiers.items():
            hier_el = _sub(dim_el, "hierarchy")
            _sub(hier_el, "name", hier_name)
            for lv_name, ref in levels:
                lv_el = _sub(hier_el, "level")
                _sub(lv_el, "name", lv_name)
                _sub(lv_el, "refobj", ref)

    for row in sheets.get("fact_calc", {}).get("rows", []):
        name, agg, datatype, expr = (row + [""] * 4)[:4]
        m = _sub(ns_el, "measure")
        _sub(m, "name", name)
        _sub(m, "regularAggregate", agg)
        _sub(m, "datatype", datatype)
        if expr:
            _sub(m, "expression", expr)
