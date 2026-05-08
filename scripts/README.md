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

### 方式一：使用 init.sql（推荐）

先用 `python manage.py migrate` 创建 Django 系统表，然后：

```bash
mysql -u root < sql/init.sql
```

### 方式二：手动导入生成的数据

```bash
# 1. 创建数据库和表结构
mysql -u root < sql/schema.sql

# 2. 创建测试用户和族谱（必须，因为 member 有外键到 genealogy）
mysql -u root gene_tree -e "
INSERT INTO user (user_id, password, username, email, is_superuser, is_staff, is_active, date_joined, first_name, last_name)
VALUES (1, '!', 'demo_admin', 'admin@test.com', 0, 0, 1, NOW(), '', ''),
       (2, '!', 'demo_editor', 'editor@test.com', 0, 0, 1, NOW(), '', '');

INSERT INTO genealogy (genealogy_id, title, surname, created_at, created_by_id)
VALUES (1, '张氏族谱（小）', '张', NOW(), 1),
       (2, '李氏族谱（中）', '李', NOW(), 1),
       (3, '王氏族谱（大）', '王', NOW(), 1);

INSERT INTO genealogy_user (user_id, genealogy_id, role)
VALUES (1, 1, 'owner'), (1, 2, 'owner'), (1, 3, 'owner'),
       (2, 1, 'editor'), (2, 2, 'editor');
"

# 3. 导入数据（按顺序：member → parent_child → marriage）
# Windows 下使用绝对路径，注意 secure_file_priv 设置
mysql -u root gene_tree -e "
SET FOREIGN_KEY_CHECKS=0;
LOAD DATA INFILE 'C:/path/to/sql/generated/small/member.csv'
INTO TABLE member FIELDS TERMINATED BY ',' ENCLOSED BY '\"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS;
LOAD DATA INFILE 'C:/path/to/sql/generated/small/parent_child.csv'
INTO TABLE parent_child FIELDS TERMINATED BY ',' ENCLOSED BY '\"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS;
LOAD DATA INFILE 'C:/path/to/sql/generated/small/marriage.csv'
INTO TABLE marriage FIELDS TERMINATED BY ',' ENCLOSED BY '\"'
LINES TERMINATED BY '\n' IGNORE 1 ROWS;
SET FOREIGN_KEY_CHECKS=1;
"
```

> **注意**：如需同时导入三个数据集，依次替换路径中的 `small` 为 `medium`、`large` 即可。

### 方式三：PowerShell 一键导入脚本

```powershell
# 导入单个数据集
$base = "D:\VS77\Course\DB\exp\gene-tree\sql\generated\small"
mysql -u root gene_tree -e "SET FOREIGN_KEY_CHECKS=0;"
Get-Content "$base\member.csv" | mysql -u root gene_tree -e "LOAD DATA LOCAL INFILE '/dev/stdin' INTO TABLE member FIELDS TERMINATED BY ',' ENCLOSED BY '`"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;"
Get-Content "$base\parent_child.csv" | mysql -u root gene_tree -e "LOAD DATA LOCAL INFILE '/dev/stdin' INTO TABLE parent_child FIELDS TERMINATED BY ',' ENCLOSED BY '`"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;"
Get-Content "$base\marriage.csv" | mysql -u root gene_tree -e "LOAD DATA LOCAL INFILE '/dev/stdin' INTO TABLE marriage FIELDS TERMINATED BY ',' ENCLOSED BY '`"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;"
mysql -u root gene_tree -e "SET FOREIGN_KEY_CHECKS=1;"
```

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
