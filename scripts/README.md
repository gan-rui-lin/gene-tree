# 造数据脚本

## 快速开始

```bash
conda activate gene-tree

# 一键生成全部数据集（small / medium / large）
python scripts/generate_all.py

# 或单独生成某个数据集
python scripts/generate_family_csv.py --out-dir sql/generated/small \
    --target 500 --seed 42 --genealogy-id 1 \
    --start-member-id 10000 --start-marriage-id 10000 \
    --start-year 1920 --founders 30 --gen-span 15
```

## 数据集规格

| 数据集 | genealogy_id | 成员数 | 婚姻数 | 年份范围 | 用途 |
|--------|-------------|--------|--------|----------|------|
| `sql/generated/small/` | 1 | 500 | 154 | 1917~2026 | 开发联调 |
| `sql/generated/medium/` | 2 | 5,000 | 1,817 | 1807~2026 | 功能测试 |
| `sql/generated/large/` | 3 | 50,000 | 14,475 | 1778~2023 | 性能压测 |

三个数据集可同时导入同一数据库（genealogy_id 和 member_id 范围互不重叠）。

每种数据集包含三个 CSV 文件：
- `member.csv` — 成员表（member_id, genealogy_id, name, gender, birth_year, death_year, biography）
- `parent_child.csv` — 亲子关系表（parent_id, child_id, relation_type）
- `marriage.csv` — 婚姻表（marriage_id, spouse1_id, spouse2_id, start_date, end_date, status）

## 导入 MySQL

### 前置条件

```bash
# 1. 先用 Django 创建系统表
python manage.py migrate

# 2. 导入基础测试数据（用户 + 族谱1 + 成员）
mysql -u root -p gene_tree < sql/init.sql
```

此时数据库中已有：user 1(demo_admin)、user 2(demo_editor)、genealogy 1。

### 导入生成的三个族谱数据

```bash
# 一条命令导入全部三个数据集（需从项目根目录执行）
mysql -u root -p --local-infile=1 gene_tree < sql/import_generated.sql
```

`import_generated.sql` 会自动完成：
1. 创建 genealogy 2（李氏中型族谱）和 genealogy 3（王氏大型族谱）
2. 将 demo_admin 绑定为三个族谱的 owner
3. 按 member → parent_child → marriage 顺序导入三个数据集
4. 最后输出验证统计

导入后预期：
| genealogy_id | 姓氏 | 成员数 | 婚姻数 |
|---|---|---|---|
| 1 (small) | 江 | 500 | 154 |
| 2 (medium) | 朱 | 5,000 | 1,817 |
| 3 (large) | 伍 | 50,000 | 14,475 |

### 常见问题

- **`--local-infile=1` 必须加**：CSV 文件不在 MySQL 服务端目录，需用 `LOCAL INFILE` 从客户端读取
- **必须从项目根目录执行**：SQL 中用的是相对路径 `sql/generated/...`
- **如报错 `The used command is not allowed`**：MySQL 需开启 `local_infile`，执行 `SET GLOBAL local_infile = 1;`

## 参数说明

`generate_family_csv.py` 支持的参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--out-dir` | `sql/generated` | 输出目录 |
| `--target` | 500 | 目标成员数 |
| `--seed` | 2026 | 随机种子（保证复现） |
| `--genealogy-id` | 1 | 族谱 ID |
| `--start-member-id` | 10000 | 起始成员 ID |
| `--start-marriage-id` | 10000 | 起始婚姻 ID |
| `--start-year` | 0（自动） | 族谱起始年份（0 = 根据 target 自动计算） |
| `--founders` | 0（自动） | 创始夫妇数量（0 = 根据 target 自动计算） |
| `--gen-span` | 20 | 每代年数跨度（18~25 为合理范围） |
| `--min-children` | 3 | 每对夫妇最少子女数 |
| `--max-children` | 5 | 每对夫妇最多子女数 |

## 数据生成规则

- **中文姓名**：100 姓氏 + 50 男名 + 50 女名随机组合，30% 概率双字名
- **婚配约束**：男 22~60 岁、女 20~55 岁、年龄差 ≤10 年、近亲三代不婚配
- **在世概率**：按年龄动态计算（≤30 岁 98%、≤50 岁 90%、≤70 岁 50%、≤85 岁 15%）
- **起始年份**：根据目标人数自动推算，确保族谱延续到 2026 年仍有在世成员
- **异常防护**：自动防止自环、重复亲子关系、重复婚姻
