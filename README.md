# 族谱管理系统（Django + MySQL）

这是一个基于 Django 的族谱管理系统，支持：
- 用户注册 / 登录
- 族谱创建与协作邀请
- 成员 CRUD（含页面内联更新/删除）与姓名前缀模糊查询（`LIKE 'xxx%'`）
- 祖先 / 后代递归查询
- 亲缘关系最短路径查询
- 树形后代展示
- 角色权限控制（owner/editor 可写，viewer 只读）

---

## 初次运行（Windows + Conda）

按下面顺序执行即可（干净环境推荐流程）：

### 1. 创建并激活 Conda 环境
```bash
conda create -n gene-tree python=3.11 -y
conda activate gene-tree
pip install -r requirementlist.txt
```

### 2. 准备 `.env`
```bash
copy .env.example .env
```

默认本地数据库配置：
- `GENE_TREE_DB_NAME=gene_tree`
- `GENE_TREE_DB_USER=root`
- `GENE_TREE_DB_PASSWORD=`（空密码）
- `GENE_TREE_DB_HOST=127.0.0.1`
- `GENE_TREE_DB_PORT=3306`

### 3. 创建数据库
```sql
CREATE DATABASE gene_tree CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 执行 Django 迁移（创建表结构）
```bash
python manage.py migrate
```

> 注意：`parent_child` 已按报告改为复合主键 `(parent_id, child_id)`。
> 如果你之前已经按旧版本迁移过数据库（含 `parent_child_id`），建议重建数据库后重新 `migrate`，避免主键结构不一致。

### 5. 导入测试数据
```bash
mysql -u root -p gene_tree < sql/init.sql
```

PowerShell 也可用：
```powershell
Get-Content .\sql\init.sql | mysql -u root -p gene_tree
```

### 6. 启动项目
```bash
python manage.py runserver
```

访问：`http://127.0.0.1:8000/`

### 7. 默认测试账号（初始化后可用）
- 管理员：`demo_admin / Admin@12345`（owner）
- 编辑者：`demo_editor / Editor@12345`（editor）

---

## 为什么要执行 `makemigrations` 和 `migrate`？

本项目使用 Django ORM，`models.py` 是数据库结构的“代码定义”。

- `makemigrations`：根据模型变更生成迁移文件（结构变更记录）。
- `migrate`：执行迁移文件，把变更真正应用到 MySQL（建表/改表）。

这样可以保证不同环境数据库结构一致，也方便后续升级和维护。

---

## 主要页面
- `/dashboard-page`
- `/analysis-page`
- `/login-page`
- `/members-page`
- `/tree-page`

## 主要 API
- `POST /register`
- `POST /login`
- `GET /dashboard`
- `GET/POST /members`
- `GET /ancestors/{id}`
- `GET /descendants/{id}`
- `GET /relationship?id1=xxx&id2=xxx`

## 补充脚本与SQL
- 数据生成脚本：`scripts/generate_family_csv.py`
- 导入导出示例：`sql/import_export.sql`
