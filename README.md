# 族谱管理系统（Django + MySQL）

这是一个基于 Django 的族谱管理系统，支持：
- 用户注册 / 登录
- 族谱创建与协作邀请
- 成员 CRUD 与姓名前缀模糊查询（`LIKE 'xxx%'`）
- 祖先 / 后代递归查询
- 亲缘关系最短路径查询
- 树形后代展示

---

## 初次运行（Windows + Conda）

### 1. 创建并激活 Conda 环境
```bash
conda create -n gene-tree python=3.11 -y
conda activate gene-tree
pip install -r requirementlist.txt
```

### 2. 准备 `.env`
项目已提供 `.env.example`，复制一份为 `.env`：

```bash
copy .env.example .env
```

默认本地数据库配置为：
- `GENE_TREE_DB_HOST=127.0.0.1`
- `GENE_TREE_DB_PORT=3306`
- `GENE_TREE_DB_USER=root`
- `GENE_TREE_DB_PASSWORD=`（空密码）
- `GENE_TREE_DB_NAME=gene_tree`

### 3. 在 MySQL 中创建数据库
```sql
CREATE DATABASE gene_tree CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 初始化表结构并启动
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

访问：`http://127.0.0.1:8000/`

---

## 为什么要执行 `makemigrations` 和 `migrate`？

本项目使用 Django ORM，`models.py` 是数据库结构的“代码定义”。

- `makemigrations`：根据模型变更生成迁移文件（结构变更记录）。
- `migrate`：执行迁移文件，把变更真正应用到 MySQL（建表/改表）。

这样可以保证不同环境数据库结构一致，也方便后续升级和维护。

---

## 主要页面
- `/login-page`
- `/members-page`
- `/tree-page`

## 主要 API
- `POST /register`
- `POST /login`
- `GET/POST /members`
- `GET /ancestors/{id}`
- `GET /descendants/{id}`
- `GET /relationship?id1=xxx&id2=xxx`
