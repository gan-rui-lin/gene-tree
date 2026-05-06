from collections import defaultdict, deque

from django.db import connection

from .models import Marriage, Member, ParentChild


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
