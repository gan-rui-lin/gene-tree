from collections import defaultdict, deque

from django.db import connection
from django.utils import timezone

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


def export_genealogy_tree(genealogy_id):
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
    return {
        "genealogy_id": genealogy_id,
        "exported_at": timezone.now().isoformat(),
        "total_members": len(members),
        "total_parent_child_links": len(parent_child_rows),
        "total_marriages": len(marriage_rows),
        "roots": roots,
        "nodes": nodes,
        "marriages": marriages,
    }


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
        JOIN member m
            ON (ma.spouse1_id = %s AND m.member_id = ma.spouse2_id)
            OR (ma.spouse2_id = %s AND m.member_id = ma.spouse1_id)

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


def fetch_longest_lifespan_generation(genealogy_id):
    sql = """
    WITH RECURSIVE generation_tree AS (
        SELECT
            m.member_id,
            1 AS generation
        FROM member m
        LEFT JOIN parent_child pc ON pc.child_id = m.member_id
        WHERE m.genealogy_id = %s
          AND pc.child_id IS NULL

        UNION ALL

        SELECT
            pc.child_id AS member_id,
            gt.generation + 1 AS generation
        FROM generation_tree gt
        JOIN parent_child pc ON pc.parent_id = gt.member_id
        JOIN member c ON c.member_id = pc.child_id
        WHERE c.genealogy_id = %s
    ),
    member_generation AS (
        SELECT member_id, MIN(generation) AS generation
        FROM generation_tree
        GROUP BY member_id
    ),
    generation_lifespan AS (
        SELECT
            mg.generation,
            AVG(COALESCE(m.death_year, YEAR(CURDATE())) - m.birth_year) AS avg_lifespan
        FROM member_generation mg
        JOIN member m ON m.member_id = mg.member_id
        WHERE m.birth_year IS NOT NULL
        GROUP BY mg.generation
    )
    SELECT generation, avg_lifespan
    FROM generation_lifespan
    ORDER BY avg_lifespan DESC
    LIMIT 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [genealogy_id, genealogy_id])
        row = cursor.fetchone()
        if not row:
            return {}
        return {"generation": row[0], "avg_lifespan": float(row[1])}


def fetch_unmarried_male_over_50(genealogy_id):
    sql = """
    SELECT
        m.member_id,
        m.name,
        m.gender,
        m.birth_year,
        (YEAR(CURDATE()) - m.birth_year) AS age
    FROM member m
    LEFT JOIN marriage ma
        ON m.member_id = ma.spouse1_id
        OR m.member_id = ma.spouse2_id
    WHERE m.genealogy_id = %s
      AND m.gender = 'M'
      AND m.birth_year IS NOT NULL
      AND (YEAR(CURDATE()) - m.birth_year) > 50
      AND ma.marriage_id IS NULL
    ORDER BY age DESC, m.member_id;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [genealogy_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_early_born_members(genealogy_id):
    sql = """
    WITH RECURSIVE generation_tree AS (
        SELECT
            m.member_id,
            1 AS generation
        FROM member m
        LEFT JOIN parent_child pc ON pc.child_id = m.member_id
        WHERE m.genealogy_id = %s
          AND pc.child_id IS NULL

        UNION ALL

        SELECT
            pc.child_id AS member_id,
            gt.generation + 1 AS generation
        FROM generation_tree gt
        JOIN parent_child pc ON pc.parent_id = gt.member_id
        JOIN member c ON c.member_id = pc.child_id
        WHERE c.genealogy_id = %s
    ),
    member_generation AS (
        SELECT member_id, MIN(generation) AS generation
        FROM generation_tree
        GROUP BY member_id
    ),
    generation_avg_birth AS (
        SELECT
            mg.generation,
            AVG(m.birth_year) AS avg_birth_year
        FROM member_generation mg
        JOIN member m ON m.member_id = mg.member_id
        WHERE m.birth_year IS NOT NULL
        GROUP BY mg.generation
    )
    SELECT
        m.member_id,
        m.name,
        mg.generation,
        m.birth_year,
        gab.avg_birth_year
    FROM member_generation mg
    JOIN member m ON m.member_id = mg.member_id
    JOIN generation_avg_birth gab ON gab.generation = mg.generation
    WHERE m.birth_year IS NOT NULL
      AND m.birth_year < gab.avg_birth_year
    ORDER BY mg.generation, m.birth_year, m.member_id;
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
