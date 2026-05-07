-- 1) 祖先查询（递归 CTE）
-- 输入参数：:id
WITH RECURSIVE ancestors AS (
    SELECT parent_id, child_id
    FROM parent_child
    WHERE child_id = :id

    UNION ALL

    SELECT pc.parent_id, pc.child_id
    FROM parent_child pc
    JOIN ancestors a ON pc.child_id = a.parent_id
)
SELECT *
FROM ancestors;

-- 2) 后代查询（递归 CTE）
-- 输入参数：:id
WITH RECURSIVE descendants AS (
    SELECT child_id
    FROM parent_child
    WHERE parent_id = :id

    UNION ALL

    SELECT pc.child_id
    FROM parent_child pc
    JOIN descendants d ON pc.parent_id = d.child_id
)
SELECT *
FROM descendants;

-- 3) 配偶查询
-- 输入参数：:id
SELECT spouse2_id
FROM marriage
WHERE spouse1_id = :id

UNION

SELECT spouse1_id
FROM marriage
WHERE spouse2_id = :id;

-- 4) 亲缘路径查询（SQL + BFS 思路）
-- Step A: 构建无向边集合（父子关系 + 婚姻关系）
SELECT parent_id AS node_a, child_id AS node_b, 'parent_child' AS edge_type FROM parent_child
UNION ALL
SELECT child_id AS node_a, parent_id AS node_b, 'parent_child' AS edge_type FROM parent_child
UNION ALL
SELECT spouse1_id AS node_a, spouse2_id AS node_b, 'marriage' AS edge_type FROM marriage
UNION ALL
SELECT spouse2_id AS node_a, spouse1_id AS node_b, 'marriage' AS edge_type FROM marriage;

-- Step B: 在应用层按层执行 BFS
-- SELECT node_b FROM edge_set WHERE node_a IN (:current_frontier) AND node_b NOT IN (:visited);
