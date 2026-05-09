from collections import defaultdict, deque
from html import escape as html_escape

from django.db import connection
from django.db import transaction
from django.utils import timezone

from .models import Marriage, Member, MemberGenerationCache, ParentChild


def fetch_ancestors(member_id):
    sql = """
    WITH RECURSIVE ancestors AS (
        SELECT
            pc.parent_id AS member_id,
            pc.child_id,
            pc.relation_type,
            1 AS depth
        FROM parent_child pc
        WHERE pc.child_id = %s

        UNION ALL

        SELECT
            pc.parent_id AS member_id,
            pc.child_id,
            pc.relation_type,
            a.depth + 1 AS depth
        FROM parent_child pc
        JOIN ancestors a ON pc.child_id = a.member_id
    )
    SELECT DISTINCT
        a.member_id,
        m.name,
        a.depth
    FROM ancestors a
    JOIN member m ON m.member_id = a.member_id
    ORDER BY a.depth ASC, a.member_id ASC;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [member_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_descendants(member_id):
    sql = """
    WITH RECURSIVE descendants AS (
        SELECT
            pc.child_id AS member_id,
            pc.parent_id,
            pc.relation_type,
            1 AS depth
        FROM parent_child pc
        WHERE pc.parent_id = %s

        UNION ALL

        SELECT
            pc.child_id AS member_id,
            pc.parent_id,
            pc.relation_type,
            d.depth + 1 AS depth
        FROM parent_child pc
        JOIN descendants d ON pc.parent_id = d.member_id
    )
    SELECT DISTINCT
        d.member_id,
        m.name,
        d.depth
    FROM descendants d
    JOIN member m ON m.member_id = d.member_id
    ORDER BY d.depth ASC, d.member_id ASC;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [member_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_descendant_tree(root_member_id, max_depth=10):
    root = Member.objects.filter(member_id=root_member_id).first()
    if not root:
        return {}

    def build_node(member, depth):
        if depth > max_depth:
            return {"member_id": member.member_id, "name": member.name, "children": []}

        child_links = (
            ParentChild.objects.filter(parent_id=member.member_id)
            .select_related("child")
            .order_by("child__member_id")
        )
        return {
            "member_id": member.member_id,
            "name": member.name,
            "children": [build_node(link.child, depth + 1) for link in child_links],
        }

    return build_node(root, depth=1)


def build_ancestor_tree(root_member_id, max_depth=10):
    root = Member.objects.filter(member_id=root_member_id).first()
    if not root:
        return {}

    def build_node(member, depth):
        if depth > max_depth:
            return {
                "member_id": member.member_id,
                "name": member.name,
                "father": None,
                "mother": None,
            }

        parent_links = (
            ParentChild.objects.filter(child_id=member.member_id)
            .select_related("parent")
            .order_by("parent__member_id")
        )

        father = None
        mother = None
        for link in parent_links:
            relation_type = (link.relation_type or "").strip().lower()
            if relation_type == ParentChild.RELATION_FATHER:
                father = build_node(link.parent, depth + 1)
            elif relation_type == ParentChild.RELATION_MOTHER:
                mother = build_node(link.parent, depth + 1)

        return {
            "member_id": member.member_id,
            "name": member.name,
            "father": father,
            "mother": mother,
        }

    return build_node(root, depth=1)


def _filter_payload_by_root_member(payload, root_member_id):
    node_map = {node["member_id"]: node for node in payload.get("nodes", [])}
    if root_member_id not in node_map:
        return None

    descendants = set()
    queue = deque([root_member_id])
    while queue:
        current = queue.popleft()
        if current in descendants:
            continue
        descendants.add(current)
        node = node_map.get(current, {})
        for child in node.get("children", []):
            child_id = child.get("child_id")
            if child_id in node_map and child_id not in descendants:
                queue.append(child_id)

    included = set(descendants)
    marriages_all = payload.get("marriages", [])
    changed = True
    while changed:
        changed = False
        for row in marriages_all:
            s1 = row["spouse1_id"]
            s2 = row["spouse2_id"]
            if s1 in included or s2 in included:
                if s1 in node_map and s1 not in included:
                    included.add(s1)
                    changed = True
                if s2 in node_map and s2 not in included:
                    included.add(s2)
                    changed = True

    filtered_nodes = []
    parent_ids = set()
    child_ids = set()
    for member_id in sorted(included):
        node = node_map[member_id]
        children = [c for c in node.get("children", []) if c.get("child_id") in included]
        parents = [p for p in node.get("parents", []) if p.get("parent_id") in included]
        for c in children:
            parent_ids.add(member_id)
            child_ids.add(c["child_id"])
        filtered_nodes.append({**node, "children": children, "parents": parents})

    filtered_marriages = [
        row
        for row in marriages_all
        if row["spouse1_id"] in included and row["spouse2_id"] in included
    ]
    roots = sorted(parent_ids - child_ids) if parent_ids else [root_member_id]

    return {
        **payload,
        "root_member_id": root_member_id,
        "total_members": len(filtered_nodes),
        "total_parent_child_links": sum(len(node["children"]) for node in filtered_nodes),
        "total_marriages": len(filtered_marriages),
        "roots": roots,
        "nodes": filtered_nodes,
        "marriages": filtered_marriages,
    }


def export_genealogy_tree(genealogy_id, root_member_id=None):
    members = list(
        Member.objects.filter(genealogy_id=genealogy_id)
        .values("member_id", "name", "gender", "birth_year", "death_year")
        .order_by("member_id")
    )
    parent_child_rows = list(
        ParentChild.objects.filter(
            parent__genealogy_id=genealogy_id,
            child__genealogy_id=genealogy_id,
        )
        .values("parent_id", "child_id", "relation_type")
        .order_by("parent_id", "child_id")
    )
    marriage_rows = list(
        Marriage.objects.filter(
            spouse1__genealogy_id=genealogy_id,
            spouse2__genealogy_id=genealogy_id,
        )
        .values("marriage_id", "spouse1_id", "spouse2_id", "start_date", "end_date", "status")
        .order_by("marriage_id")
    )
    marriages = [
        {
            **row,
            "start_date": row["start_date"].isoformat() if row["start_date"] else None,
            "end_date": row["end_date"].isoformat() if row["end_date"] else None,
        }
        for row in marriage_rows
    ]

    children_map = defaultdict(list)
    parents_map = defaultdict(list)
    parent_ids = set()
    child_ids = set()
    for row in parent_child_rows:
        relation_type = (row["relation_type"] or "").strip().lower()
        parent_id = row["parent_id"]
        child_id = row["child_id"]
        children_map[parent_id].append({"child_id": child_id, "relation_type": relation_type})
        parents_map[child_id].append({"parent_id": parent_id, "relation_type": relation_type})
        parent_ids.add(parent_id)
        child_ids.add(child_id)

    for member_id in children_map:
        children_map[member_id].sort(key=lambda item: item["child_id"])
    for member_id in parents_map:
        parents_map[member_id].sort(key=lambda item: item["parent_id"])

    roots = sorted(parent_ids - child_ids)
    nodes = [
        {
            **member,
            "parents": parents_map.get(member["member_id"], []),
            "children": children_map.get(member["member_id"], []),
        }
        for member in members
    ]
    payload = {
        "genealogy_id": genealogy_id,
        "exported_at": timezone.now().isoformat(),
        "total_members": len(members),
        "total_parent_child_links": len(parent_child_rows),
        "total_marriages": len(marriage_rows),
        "roots": roots,
        "nodes": nodes,
        "marriages": marriages,
    }
    if root_member_id is not None:
        filtered = _filter_payload_by_root_member(payload, root_member_id)
        if filtered is None:
            return None
        return filtered
    return payload


def _dot_escape(value):
    text = str(value or "")
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _build_tree_layout(payload):
    nodes = payload.get("nodes", [])
    if not nodes:
        return {}, {}, 180, 60, 160, 42

    node_ids = sorted(node["member_id"] for node in nodes)
    edges = []
    children_map = defaultdict(list)
    indegree = {member_id: 0 for member_id in node_ids}

    for node in nodes:
        parent_id = node["member_id"]
        for child in node.get("children", []):
            child_id = child.get("child_id")
            if child_id not in indegree:
                continue
            relation_type = (child.get("relation_type") or "").strip().lower()
            edges.append((parent_id, child_id, relation_type))
            children_map[parent_id].append((child_id, relation_type))
            indegree[child_id] += 1

    roots = payload.get("roots") or sorted(
        [member_id for member_id, degree in indegree.items() if degree == 0]
    )
    if not roots:
        roots = [node_ids[0]]

    queue = deque(sorted(roots))
    level_map = {member_id: 0 for member_id in roots}
    indegree_work = indegree.copy()

    while queue:
        current = queue.popleft()
        for child_id, _relation_type in children_map.get(current, []):
            level_map[child_id] = max(level_map.get(child_id, 0), level_map[current] + 1)
            indegree_work[child_id] -= 1
            if indegree_work[child_id] == 0:
                queue.append(child_id)

    unresolved = [member_id for member_id in node_ids if member_id not in level_map]
    fallback_level = max(level_map.values(), default=-1) + 1
    for idx, member_id in enumerate(unresolved):
        level_map[member_id] = fallback_level + idx

    level_nodes = defaultdict(list)
    for member_id, level in level_map.items():
        level_nodes[level].append(member_id)
    for level in level_nodes:
        level_nodes[level].sort()

    node_width = 160
    node_height = 42
    x_gap = 42
    y_gap = 84
    margin_x = 24
    margin_y = 24

    max_per_level = max((len(items) for items in level_nodes.values()), default=1)
    total_width = margin_x * 2 + max_per_level * node_width + max(0, max_per_level - 1) * x_gap
    max_level = max(level_nodes.keys(), default=0)
    total_height = margin_y * 2 + (max_level + 1) * node_height + max_level * y_gap

    positions = {}
    for level in sorted(level_nodes.keys()):
        items = level_nodes[level]
        count = len(items)
        row_width = count * node_width + max(0, count - 1) * x_gap
        start_x = (total_width - row_width) / 2
        y = margin_y + level * (node_height + y_gap)
        for idx, member_id in enumerate(items):
            x = start_x + idx * (node_width + x_gap)
            positions[member_id] = (x, y)

    return positions, edges, total_width, total_height, node_width, node_height


def export_genealogy_tree_dot(genealogy_id, root_member_id=None):
    payload = export_genealogy_tree(genealogy_id, root_member_id=root_member_id)
    if payload is None:
        return None
    lines = [
        f"digraph genealogy_{genealogy_id} {{",
        '  graph [rankdir=TB, splines=ortho, nodesep=0.35, ranksep=0.65, pad="0.15"];',
        '  node [shape=box, style="rounded,filled", fillcolor="#eef1ff", color="#8ea0ff",',
        '        fontname="Microsoft YaHei", fontsize=10, penwidth=1.1];',
        '  edge [color="#9aa4b2", arrowsize=0.7, penwidth=1.0];',
    ]

    for node in payload["nodes"]:
        member_id = node["member_id"]
        name = _dot_escape(node["name"])
        lines.append(f'  n_{member_id} [label="{member_id} - {name}"];')

    for node in payload["nodes"]:
        parent_id = node["member_id"]
        for child in node.get("children", []):
            child_id = child["child_id"]
            relation_type = (child.get("relation_type") or "").strip().lower()
            if relation_type == "father":
                color = "#457b9d"
            elif relation_type == "mother":
                color = "#d63384"
            else:
                color = "#9aa4b2"
            lines.append(f'  n_{parent_id} -> n_{child_id} [color="{color}"];')

    for row in payload.get("marriages", []):
        spouse1_id = row["spouse1_id"]
        spouse2_id = row["spouse2_id"]
        lines.append(
            f'  n_{spouse1_id} -> n_{spouse2_id} [dir=none, style=dashed, color="#f4a261", constraint=false];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_year_range(node):
    birth = node.get("birth_year")
    death = node.get("death_year")
    left = str(birth) if birth is not None else ""
    right = str(death) if death is not None else ""
    if not left and not right:
        return "-"
    return f"{left}-{right}"


def _build_family_units(payload):
    node_map = {node["member_id"]: node for node in payload.get("nodes", [])}
    marriages = sorted(payload.get("marriages", []), key=lambda row: row.get("marriage_id", 0))

    spouse_marriages = defaultdict(list)
    for row in marriages:
        spouse_marriages[row["spouse1_id"]].append(row)
        spouse_marriages[row["spouse2_id"]].append(row)

    primary_marriage_by_member = {}
    for member_id, rows in spouse_marriages.items():
        if rows:
            primary_marriage_by_member[member_id] = rows[0]

    units = []
    member_to_unit = {}
    used_members = set()

    for row in marriages:
        spouse1_id = row["spouse1_id"]
        spouse2_id = row["spouse2_id"]
        if spouse1_id not in node_map or spouse2_id not in node_map:
            continue
        if (
            primary_marriage_by_member.get(spouse1_id) != row
            or primary_marriage_by_member.get(spouse2_id) != row
        ):
            continue

        unit_id = f"u_m_{row['marriage_id']}"
        members = [spouse1_id, spouse2_id]
        units.append({"unit_id": unit_id, "members": members, "kind": "couple"})
        member_to_unit[spouse1_id] = unit_id
        member_to_unit[spouse2_id] = unit_id
        used_members.update(members)

    for member_id in sorted(node_map.keys()):
        if member_id in used_members:
            continue
        unit_id = f"u_s_{member_id}"
        units.append({"unit_id": unit_id, "members": [member_id], "kind": "single"})
        member_to_unit[member_id] = unit_id

    parent_edges = set()
    for node in node_map.values():
        child_id = node["member_id"]
        target_unit = member_to_unit.get(child_id)
        if not target_unit:
            continue

        father_ids = [
            p["parent_id"]
            for p in node.get("parents", [])
            if (p.get("relation_type") or "").strip().lower() == "father"
        ]
        mother_ids = [
            p["parent_id"]
            for p in node.get("parents", [])
            if (p.get("relation_type") or "").strip().lower() == "mother"
        ]
        source_unit = None
        if father_ids:
            source_unit = member_to_unit.get(father_ids[0])
        if not source_unit and mother_ids:
            source_unit = member_to_unit.get(mother_ids[0])

        if source_unit and source_unit != target_unit:
            parent_edges.add((source_unit, target_unit))

    units_by_id = {unit["unit_id"]: unit for unit in units}
    return units, units_by_id, member_to_unit, sorted(parent_edges), node_map


def _layout_family_units(units, parent_edges):
    children_map = defaultdict(list)
    indegree = {unit["unit_id"]: 0 for unit in units}

    for source_id, target_id in parent_edges:
        if source_id not in indegree or target_id not in indegree:
            continue
        children_map[source_id].append(target_id)
        indegree[target_id] += 1

    roots = sorted([unit_id for unit_id, degree in indegree.items() if degree == 0])
    if not roots and units:
        roots = [sorted(indegree.keys())[0]]

    queue = deque(roots)
    level_map = {unit_id: 0 for unit_id in roots}
    indegree_work = indegree.copy()
    while queue:
        current = queue.popleft()
        for child_id in children_map.get(current, []):
            level_map[child_id] = max(level_map.get(child_id, 0), level_map[current] + 1)
            indegree_work[child_id] -= 1
            if indegree_work[child_id] == 0:
                queue.append(child_id)

    unresolved = [unit_id for unit_id in indegree.keys() if unit_id not in level_map]
    fallback_level = max(level_map.values(), default=-1) + 1
    for idx, unit_id in enumerate(sorted(unresolved)):
        level_map[unit_id] = fallback_level + idx

    level_units = defaultdict(list)
    for unit in units:
        unit_id = unit["unit_id"]
        level_units[level_map.get(unit_id, 0)].append(unit_id)

    for level in level_units:
        level_units[level].sort(
            key=lambda unit_id: (
                0 if unit_id.startswith("u_s_") else 1,
                int(unit_id.split("_")[-1]) if unit_id.split("_")[-1].isdigit() else 0,
            )
        )

    node_width = 220
    node_height = 78
    x_gap = 42
    y_gap = 86
    margin_x = 32
    margin_y = 56

    max_per_level = max((len(items) for items in level_units.values()), default=1)
    total_width = margin_x * 2 + max_per_level * node_width + max(0, max_per_level - 1) * x_gap
    max_level = max(level_units.keys(), default=0)
    total_height = margin_y * 2 + (max_level + 1) * node_height + max_level * y_gap + 40

    positions = {}
    for level in sorted(level_units.keys()):
        items = level_units[level]
        count = len(items)
        row_width = count * node_width + max(0, count - 1) * x_gap
        start_x = (total_width - row_width) / 2
        y = margin_y + level * (node_height + y_gap)
        for idx, unit_id in enumerate(items):
            x = start_x + idx * (node_width + x_gap)
            positions[unit_id] = (x, y)

    return positions, total_width, total_height, node_width, node_height


def export_genealogy_tree_svg(genealogy_id, root_member_id=None):
    payload = export_genealogy_tree(genealogy_id, root_member_id=root_member_id)
    if payload is None:
        return None
    units, units_by_id, _member_to_unit, parent_edges, node_map = _build_family_units(payload)
    positions, width, height, node_width, node_height = _layout_family_units(units, parent_edges)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        "  <defs>",
        "    <style>",
        "      .card { fill: #f5fbf7; stroke: #2da36b; stroke-width: 1.2; }",
        "      .card-head { fill: #3aa66d; }",
        "      .name { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 13px; font-weight: 700; fill: #ffffff; }",
        "      .years { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 11px; fill: #1f3d2a; }",
        "      .edge { fill: none; stroke: #2da36b; stroke-width: 1.7; }",
        "      .legend-title { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 700; fill: #2b2d42; }",
        "      .legend-text { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 11px; fill: #4a5568; }",
        "    </style>",
        "  </defs>",
    ]

    legend_x = width - 250
    if legend_x < 20:
        legend_x = 20
    lines.extend(
        [
            f'  <rect x="{legend_x:.1f}" y="12" width="230" height="58" rx="8" ry="8" fill="#ffffff" stroke="#dfe5e2" />',
            f'  <text class="legend-title" x="{legend_x + 10:.1f}" y="30">图例</text>',
            f'  <line x1="{legend_x + 12:.1f}" y1="44" x2="{legend_x + 44:.1f}" y2="44" class="edge" />',
            f'  <text class="legend-text" x="{legend_x + 52:.1f}" y="48">亲子关系连线</text>',
            f'  <rect x="{legend_x + 12:.1f}" y="53" width="26" height="10" class="card-head" />',
            f'  <text class="legend-text" x="{legend_x + 52:.1f}" y="62">家庭节点（夫妻同框）</text>',
        ]
    )

    for source_id, target_id in parent_edges:
        if source_id not in positions or target_id not in positions:
            continue
        px, py = positions[source_id]
        cx, cy = positions[target_id]
        x1 = px + node_width / 2
        y1 = py + node_height
        x2 = cx + node_width / 2
        y2 = cy
        c1y = y1 + (y2 - y1) * 0.42
        c2y = y2 - (y2 - y1) * 0.42
        lines.append(
            f'  <path class="edge" d="M {x1:.1f} {y1:.1f} C {x1:.1f} {c1y:.1f}, {x2:.1f} {c2y:.1f}, {x2:.1f} {y2:.1f}" />'
        )

    for unit in units:
        unit_id = unit["unit_id"]
        if unit_id not in positions:
            continue
        x, y = positions[unit_id]
        member_ids = unit["members"]
        members = [node_map[mid] for mid in member_ids if mid in node_map]
        if not members:
            continue

        names = "   ".join(member.get("name", "") for member in members)
        years = "   ".join(_format_year_range(member) for member in members)
        names = html_escape(names)
        years = html_escape(years)

        lines.append(f'  <rect class="card" x="{x:.1f}" y="{y:.1f}" width="{node_width}" height="{node_height}" rx="5" ry="5" />')
        lines.append(
            f'  <rect class="card-head" x="{x:.1f}" y="{y:.1f}" width="{node_width}" height="34" rx="5" ry="5" />'
        )
        lines.append(
            f'  <rect x="{x:.1f}" y="{y + 29:.1f}" width="{node_width}" height="5" fill="#3aa66d" />'
        )
        lines.append(
            f'  <text class="name" x="{x + node_width / 2:.1f}" y="{y + 22:.1f}" text-anchor="middle">{names}</text>'
        )
        lines.append(
            f'  <text class="years" x="{x + node_width / 2:.1f}" y="{y + 56:.1f}" text-anchor="middle">{years}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def export_genealogy_tree_drawio(genealogy_id, root_member_id=None):
    payload = export_genealogy_tree(genealogy_id, root_member_id=root_member_id)
    if payload is None:
        return None
    positions, edges, width, height, node_width, node_height = _build_tree_layout(payload)
    modified = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f'<mxfile host="app.diagrams.net" modified="{modified}" agent="gene-tree" version="24.7.17" type="device">',
        f'  <diagram id="genealogy-{genealogy_id}" name="Genealogy {genealogy_id}">',
        f'    <mxGraphModel dx="{int(width) + 80}" dy="{int(height) + 80}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(width) + 120}" pageHeight="{int(height) + 120}" math="0" shadow="0">',
        "      <root>",
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
    ]

    for node in payload.get("nodes", []):
        member_id = node["member_id"]
        x, y = positions.get(member_id, (24, 24))
        label = html_escape(f'{member_id} - {node.get("name", "")}', quote=True)
        lines.extend(
            [
                f'        <mxCell id="n_{member_id}" value="{label}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#eef1ff;strokeColor=#8ea0ff;fontColor=#2b2d42;" vertex="1" parent="1">',
                f'          <mxGeometry x="{x:.1f}" y="{y:.1f}" width="{node_width}" height="{node_height}" as="geometry" />',
                "        </mxCell>",
            ]
        )

    edge_idx = 1
    for parent_id, child_id, relation_type in edges:
        color = "#9aa4b2"
        if relation_type == "father":
            color = "#457b9d"
        elif relation_type == "mother":
            color = "#d63384"
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            f"html=1;strokeColor={color};endArrow=block;endFill=1;"
        )
        lines.extend(
            [
                f'        <mxCell id="e_{edge_idx}" style="{style}" edge="1" parent="1" source="n_{parent_id}" target="n_{child_id}">',
                '          <mxGeometry relative="1" as="geometry" />',
                "        </mxCell>",
            ]
        )
        edge_idx += 1

    for row in payload.get("marriages", []):
        s1 = row["spouse1_id"]
        s2 = row["spouse2_id"]
        if s1 not in positions or s2 not in positions:
            continue
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            "html=1;strokeColor=#f4a261;dashed=1;endArrow=none;"
        )
        lines.extend(
            [
                f'        <mxCell id="e_{edge_idx}" style="{style}" edge="1" parent="1" source="n_{s1}" target="n_{s2}">',
                '          <mxGeometry relative="1" as="geometry" />',
                "        </mxCell>",
            ]
        )
        edge_idx += 1

    lines.extend(
        [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
        ]
    )
    return "\n".join(lines) + "\n"


def shortest_relationship_path(member_id_1, member_id_2):
    start = Member.objects.filter(member_id=member_id_1).first()
    target = Member.objects.filter(member_id=member_id_2).first()

    if not start or not target:
        return []
    if start.genealogy_id != target.genealogy_id:
        return []

    genealogy_id = start.genealogy_id
    graph = defaultdict(list)

    parent_child_rows = ParentChild.objects.filter(parent__genealogy_id=genealogy_id).values(
        "parent_id", "child_id"
    )
    for row in parent_child_rows:
        p = row["parent_id"]
        c = row["child_id"]
        graph[p].append((c, "child"))
        graph[c].append((p, "parent"))

    marriage_rows = Marriage.objects.filter(spouse1__genealogy_id=genealogy_id).values(
        "spouse1_id", "spouse2_id"
    )
    for row in marriage_rows:
        s1 = row["spouse1_id"]
        s2 = row["spouse2_id"]
        graph[s1].append((s2, "spouse"))
        graph[s2].append((s1, "spouse"))

    if start.member_id == target.member_id:
        return [{"member_id": start.member_id, "name": start.name, "via": None}]

    queue = deque([start.member_id])
    prev = {start.member_id: (None, None)}

    while queue:
        current = queue.popleft()
        if current == target.member_id:
            break

        for next_node, relation in graph[current]:
            if next_node in prev:
                continue
            prev[next_node] = (current, relation)
            queue.append(next_node)

    if target.member_id not in prev:
        return []

    route = []
    cursor = target.member_id
    while cursor is not None:
        parent, relation = prev[cursor]
        route.append((cursor, relation))
        cursor = parent
    route.reverse()

    name_map = dict(
        Member.objects.filter(member_id__in=[node_id for node_id, _ in route]).values_list(
            "member_id", "name"
        )
    )
    return [
        {"member_id": node_id, "name": name_map.get(node_id, ""), "via": relation}
        for node_id, relation in route
    ]


def fetch_spouse_and_children(member_id):
    sql = """
    SELECT relation, member_id, name, gender, birth_year, death_year
    FROM (
        SELECT
            'spouse' AS relation,
            m.member_id,
            m.name,
            m.gender,
            m.birth_year,
            m.death_year
        FROM marriage ma
        JOIN member m ON m.member_id = ma.spouse2_id
        WHERE ma.spouse1_id = %s

        UNION ALL

        SELECT
            'spouse' AS relation,
            m.member_id,
            m.name,
            m.gender,
            m.birth_year,
            m.death_year
        FROM marriage ma
        JOIN member m ON m.member_id = ma.spouse1_id
        WHERE ma.spouse2_id = %s

        UNION ALL

        SELECT
            'child' AS relation,
            c.member_id,
            c.name,
            c.gender,
            c.birth_year,
            c.death_year
        FROM parent_child pc
        JOIN member c ON c.member_id = pc.child_id
        WHERE pc.parent_id = %s
    ) t
    ORDER BY relation, member_id;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [member_id, member_id, member_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _build_generation_map(genealogy_id):
    member_ids = list(
        Member.objects.filter(genealogy_id=genealogy_id).values_list("member_id", flat=True)
    )
    if not member_ids:
        return {}

    children_map = defaultdict(list)
    gen_map = {}
    for member_id in member_ids:
        gen_map[member_id] = None

    edge_rows = ParentChild.objects.filter(
        parent__genealogy_id=genealogy_id,
        child__genealogy_id=genealogy_id,
    ).values_list("parent_id", "child_id")
    indegree = defaultdict(int)
    for parent_id, child_id in edge_rows:
        children_map[parent_id].append(child_id)
        indegree[child_id] += 1

    roots = [member_id for member_id in member_ids if indegree.get(member_id, 0) == 0]
    if not roots:
        roots = sorted(member_ids)[:1]

    queue = deque(sorted(roots))
    for root_id in roots:
        gen_map[root_id] = 1

    while queue:
        current = queue.popleft()
        current_gen = gen_map.get(current)
        if current_gen is None:
            continue
        for child_id in children_map.get(current, []):
            next_gen = current_gen + 1
            prev_gen = gen_map.get(child_id)
            if prev_gen is None or next_gen < prev_gen:
                gen_map[child_id] = next_gen
                queue.append(child_id)

    fallback = max([g for g in gen_map.values() if g is not None], default=1) + 1
    for member_id in member_ids:
        if gen_map[member_id] is None:
            gen_map[member_id] = fallback

    return gen_map


def _refresh_generation_cache(genealogy_id):
    gen_map = _build_generation_map(genealogy_id)
    rows = [
        MemberGenerationCache(
            member_id=member_id,
            genealogy_id=genealogy_id,
            generation=generation,
        )
        for member_id, generation in gen_map.items()
    ]
    with transaction.atomic():
        MemberGenerationCache.objects.filter(genealogy_id=genealogy_id).delete()
        if rows:
            MemberGenerationCache.objects.bulk_create(rows, batch_size=5000)


def _ensure_generation_cache(genealogy_id):
    member_count = Member.objects.filter(genealogy_id=genealogy_id).count()
    cache_count = MemberGenerationCache.objects.filter(genealogy_id=genealogy_id).count()
    if member_count != cache_count:
        _refresh_generation_cache(genealogy_id)


def fetch_longest_lifespan_generation(genealogy_id):
    _ensure_generation_cache(genealogy_id)
    sql = """
    WITH generation_lifespan AS (
        SELECT
            mgc.generation,
            AVG(COALESCE(m.death_year, YEAR(CURDATE())) - m.birth_year) AS avg_lifespan
        FROM member_generation_cache mgc
        JOIN member m ON m.member_id = mgc.member_id
        WHERE mgc.genealogy_id = %s
          AND m.birth_year IS NOT NULL
        GROUP BY mgc.generation
    )
    SELECT generation, avg_lifespan
    FROM generation_lifespan
    ORDER BY avg_lifespan DESC
    LIMIT 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [genealogy_id])
        row = cursor.fetchone()
        if not row:
            return {}
        return {"generation": row[0], "avg_lifespan": float(row[1])}


def fetch_unmarried_male_over_50(genealogy_id):
    sql = """
    WITH married AS (
        SELECT spouse1_id AS member_id FROM marriage
        UNION
        SELECT spouse2_id AS member_id FROM marriage
    )
    SELECT
        m.member_id,
        m.name,
        m.gender,
        m.birth_year,
        (YEAR(CURDATE()) - m.birth_year) AS age
    FROM member m
    LEFT JOIN married mr ON mr.member_id = m.member_id
    WHERE m.genealogy_id = %s
      AND m.gender = 'M'
      AND m.birth_year IS NOT NULL
      AND (YEAR(CURDATE()) - m.birth_year) > 50
      AND mr.member_id IS NULL
    ORDER BY age DESC, m.member_id;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [genealogy_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_early_born_members(genealogy_id):
    _ensure_generation_cache(genealogy_id)
    sql = """
    WITH
    generation_avg_birth AS (
        SELECT
            mgc.generation,
            AVG(m.birth_year) AS avg_birth_year
        FROM member_generation_cache mgc
        JOIN member m ON m.member_id = mgc.member_id
        WHERE mgc.genealogy_id = %s
          AND m.birth_year IS NOT NULL
        GROUP BY mgc.generation
    )
    SELECT
        m.member_id,
        m.name,
        mgc.generation,
        m.birth_year,
        gab.avg_birth_year
    FROM member_generation_cache mgc
    JOIN member m ON m.member_id = mgc.member_id
    JOIN generation_avg_birth gab ON gab.generation = mgc.generation
    WHERE mgc.genealogy_id = %s
      AND m.birth_year IS NOT NULL
      AND m.birth_year < gab.avg_birth_year
    ORDER BY mgc.generation, m.birth_year, m.member_id;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [genealogy_id, genealogy_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def shortest_relationship_path_sql_bfs(member_id_1, member_id_2):
    start = Member.objects.filter(member_id=member_id_1).first()
    target = Member.objects.filter(member_id=member_id_2).first()
    if not start or not target:
        return []
    if start.genealogy_id != target.genealogy_id:
        return []

    sql = """
    SELECT parent_id AS node_a, child_id AS node_b, 'child' AS edge_type
    FROM parent_child
    UNION ALL
    SELECT child_id AS node_a, parent_id AS node_b, 'parent' AS edge_type
    FROM parent_child
    UNION ALL
    SELECT spouse1_id AS node_a, spouse2_id AS node_b, 'spouse' AS edge_type
    FROM marriage
    UNION ALL
    SELECT spouse2_id AS node_a, spouse1_id AS node_b, 'spouse' AS edge_type
    FROM marriage
    """
    graph = defaultdict(list)
    with connection.cursor() as cursor:
        cursor.execute(sql)
        for node_a, node_b, edge_type in cursor.fetchall():
            graph[node_a].append((node_b, edge_type))

    if start.member_id == target.member_id:
        return [{"member_id": start.member_id, "name": start.name, "via": None}]

    queue = deque([start.member_id])
    prev = {start.member_id: (None, None)}
    while queue:
        current = queue.popleft()
        if current == target.member_id:
            break
        for next_node, relation in graph[current]:
            if next_node in prev:
                continue
            prev[next_node] = (current, relation)
            queue.append(next_node)

    if target.member_id not in prev:
        return []

    route = []
    cursor_id = target.member_id
    while cursor_id is not None:
        parent_id, relation = prev[cursor_id]
        route.append((cursor_id, relation))
        cursor_id = parent_id
    route.reverse()

    member_ids = [node_id for node_id, _ in route]
    name_map = dict(
        Member.objects.filter(member_id__in=member_ids).values_list("member_id", "name")
    )
    return [
        {"member_id": node_id, "name": name_map.get(node_id, ""), "via": relation}
        for node_id, relation in route
    ]
