-- 1) Ancestors query (recursive CTE)
-- Input: :member_id
WITH RECURSIVE ancestors AS (
    SELECT parent_id, child_id, relation_type, 1 AS depth
    FROM parent_child
    WHERE child_id = :member_id
    UNION ALL
    SELECT pc.parent_id, pc.child_id, pc.relation_type, a.depth + 1
    FROM parent_child pc
    JOIN ancestors a ON pc.child_id = a.parent_id
)
SELECT a.parent_id AS ancestor_id, m.name, a.depth
FROM ancestors a
JOIN member m ON m.member_id = a.parent_id
ORDER BY a.depth, ancestor_id;

-- 2) Descendants query (recursive CTE)
-- Input: :member_id
WITH RECURSIVE descendants AS (
    SELECT parent_id, child_id, relation_type, 1 AS depth
    FROM parent_child
    WHERE parent_id = :member_id
    UNION ALL
    SELECT pc.parent_id, pc.child_id, pc.relation_type, d.depth + 1
    FROM parent_child pc
    JOIN descendants d ON pc.parent_id = d.child_id
)
SELECT d.child_id AS descendant_id, m.name, d.depth
FROM descendants d
JOIN member m ON m.member_id = d.child_id
ORDER BY d.depth, descendant_id;

-- 3) Spouse query
-- Input: :member_id
SELECT spouse2_id AS spouse_id
FROM marriage
WHERE spouse1_id = :member_id
UNION
SELECT spouse1_id AS spouse_id
FROM marriage
WHERE spouse2_id = :member_id;

-- 4) Relationship shortest path (SQL + BFS idea)
-- SQL step A: build undirected edge set from parent-child + marriage
-- SQL step B: fetch neighbors for BFS iteration
--
-- Step A (edge set):
SELECT parent_id AS node_a, child_id AS node_b, 'parent_child' AS edge_type FROM parent_child
UNION ALL
SELECT child_id AS node_a, parent_id AS node_b, 'parent_child' AS edge_type FROM parent_child
UNION ALL
SELECT spouse1_id AS node_a, spouse2_id AS node_b, 'marriage' AS edge_type FROM marriage
UNION ALL
SELECT spouse2_id AS node_a, spouse1_id AS node_b, 'marriage' AS edge_type FROM marriage;
--
-- Step B (BFS each layer):
-- SELECT node_b FROM edge_set WHERE node_a IN (:current_frontier) AND node_b NOT IN (:visited);
