# 造数据脚本

## 快速开始

```bash
# 激活环境
conda activate gene-tree

# 一键生成全部数据集（small / medium / large）
python scripts/generate_all.py

# 或单独生成某个数据集
python scripts/generate_family_csv.py --out-dir sql/generated/small --genealogy-count 1 --generations 7 --min-children 3 --max-children 4 --seed 42
```

## 数据集规格

| 数据集 | 族谱数 | 成员数 | 用途 | 种子 |
|--------|--------|--------|------|------|
| `sql/generated/small/` | 1 | ~55 | 开发联调 | 42 |
| `sql/generated/medium/` | 3 | ~936 | 功能测试 | 2026 |
| `sql/generated/large/` | 10 | ~12,941 | 性能压测 | 20260108 |

每种数据集包含三个 CSV 文件：
- `member.csv` — 成员表
- `parent_child.csv` — 亲子关系表
- `marriage.csv` — 婚姻表

## 导入 MySQL

```bash
# 假设数据库 gene_tree 已创建
mysql -u root gene_tree < sql/schema.sql

# 导入数据（按顺序：member → parent_child → marriage）
mysql -u root gene_tree -e "LOAD DATA INFILE 'sql/generated/small/member.csv' INTO TABLE member FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;"
mysql -u root gene_tree -e "LOAD DATA INFILE 'sql/generated/small/parent_child.csv' INTO TABLE parent_child FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;"
mysql -u root gene_tree -e "LOAD DATA INFILE 'sql/generated/small/marriage.csv' INTO TABLE marriage FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;"
```

> Windows 下需使用绝对路径，并注意 `secure_file_priv` 设置。

## 参数说明

`generate_family_csv.py` 支持的参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--out-dir` | `sql/generated` | 输出目录 |
| `--genealogy-count` | 2 | 族谱数量 |
| `--generations` | 4 | 世代数（不含始祖） |
| `--min-children` | 1 | 每对夫妇最少子女数 |
| `--max-children` | 3 | 每对夫妇最多子女数 |
| `--seed` | 2026 | 随机种子（保证复现） |
| `--gender-ratio` | 0.5 | 男孩概率（0-1） |
| `--marriage-probability` | 0.8 | 子女配对概率（0-1） |
| `--alive-probability` | 0.3 | 在世概率，death_year 为空（0-1） |
| `--children-dist` | uniform | 子女数分布：`uniform` 或 `poisson` |
| `--avg-children` | 2.0 | 泊松分布的平均子女数 |

## 数据特性

- **中文姓名**：从 100 个姓氏 + 50 男名 + 50 女名中随机组合
- **性别保证**：每对夫妇至少有 1 男 1 女后代，确保族谱不断代
- **全局配对**：未婚男女在同族谱内跨家庭配对，实现指数增长
- **异常防护**：自动防止自环、重复亲子关系、重复婚姻
- **在世比例**：通过 `--alive-probability` 控制 `death_year` 为空的比例
