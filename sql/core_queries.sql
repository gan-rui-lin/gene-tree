-- Q1 基本查询：给定成员ID，查询其配偶及所有子女（单条SQL）
-- 输入参数：:id
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
        ON (ma.spouse1_id = :id AND m.member_id = ma.spouse2_id)
        OR (ma.spouse2_id = :id AND m.member_id = ma.spouse1_id)

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
    WHERE pc.parent_id = :id
) t
ORDER BY relation, member_id;

-- Q2 递归查询：输入成员A的ID，向上追溯所有历代祖先（Recursive CTE）
-- 输入参数：:id
WITH RECURSIVE ancestors AS (
    SELECT
        pc.parent_id AS ancestor_id,
        pc.child_id AS descendant_id,
        pc.relation_type,
        1 AS depth
    FROM parent_child pc
    WHERE pc.child_id = :id

    UNION ALL

    SELECT
        pc.parent_id AS ancestor_id,
        pc.child_id AS descendant_id,
        pc.relation_type,
        a.depth + 1 AS depth
    FROM parent_child pc
    JOIN ancestors a ON pc.child_id = a.ancestor_id
)
SELECT
    a.ancestor_id,
    m.name AS ancestor_name,
    a.relation_type,
    a.depth
FROM ancestors a
JOIN member m ON m.member_id = a.ancestor_id
ORDER BY a.depth, a.ancestor_id;

-- Q3 统计分析：统计某个家族中平均寿命最长的一代人（辈分）
-- 输入参数：:genealogy_id
WITH RECURSIVE generation_tree AS (
    SELECT
        m.member_id,
        1 AS generation
    FROM member m
    LEFT JOIN parent_child pc ON pc.child_id = m.member_id
    WHERE m.genealogy_id = :genealogy_id
      AND pc.child_id IS NULL

    UNION ALL

    SELECT
        pc.child_id AS member_id,
        gt.generation + 1 AS generation
    FROM generation_tree gt
    JOIN parent_child pc ON pc.parent_id = gt.member_id
    JOIN member c ON c.member_id = pc.child_id
    WHERE c.genealogy_id = :genealogy_id
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

-- Q4 查询所有年龄超过50岁、且没有配偶的男性成员
-- 输入参数：:genealogy_id
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
WHERE m.genealogy_id = :genealogy_id
  AND m.gender = 'M'
  AND m.birth_year IS NOT NULL
  AND (YEAR(CURDATE()) - m.birth_year) > 50
  AND ma.marriage_id IS NULL
ORDER BY age DESC, m.member_id;

-- Q5 找出出生年份早于“该辈分平均出生年份”的所有成员
-- 输入参数：:genealogy_id
WITH RECURSIVE generation_tree AS (
    SELECT
        m.member_id,
        1 AS generation
    FROM member m
    LEFT JOIN parent_child pc ON pc.child_id = m.member_id
    WHERE m.genealogy_id = :genealogy_id
      AND pc.child_id IS NULL

    UNION ALL

    SELECT
        pc.child_id AS member_id,
        gt.generation + 1 AS generation
    FROM generation_tree gt
    JOIN parent_child pc ON pc.parent_id = gt.member_id
    JOIN member c ON c.member_id = pc.child_id
    WHERE c.genealogy_id = :genealogy_id
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

-- Q6 亲缘关系路径查询（SQL + BFS 思路）
-- Step A: 构建无向边集合
SELECT parent_id AS node_a, child_id AS node_b, 'parent_child' AS edge_type FROM parent_child
UNION ALL
SELECT child_id AS node_a, parent_id AS node_b, 'parent_child' AS edge_type FROM parent_child
UNION ALL
SELECT spouse1_id AS node_a, spouse2_id AS node_b, 'marriage' AS edge_type FROM marriage
UNION ALL
SELECT spouse2_id AS node_a, spouse1_id AS node_b, 'marriage' AS edge_type FROM marriage;

-- Step B: 在应用层按层执行 BFS
-- SELECT node_b FROM edge_set WHERE node_a IN (:current_frontier) AND node_b NOT IN (:visited);
