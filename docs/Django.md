# Django 框架详解

本文档以本项目（族谱管理系统）的实际代码为例，详细解释 Django 框架的核心概念和工作原理。

---

## 一、Django 是什么

Django 是一个 **Python Web 框架**——它帮你处理 Web 开发中所有重复性的工作，让你只需要写业务逻辑。

用一个类比：**盖房子**。

| 没有框架 | 有 Django |
|---------|----------|
| 自己烧砖、和水泥、搭架子 | 直接用预制件拼装 |
| 手写 SQL 建表、手写 HTTP 解析、手写 URL 路由、手写 HTML 模板渲染 | Django 全部帮你搞定 |

Django 的核心理念是 **"不要重复自己"（DRY，Don't Repeat Yourself）**。

### Django 提供了什么

| 功能模块 | 作用 | 本项目中的体现 |
|---------|------|---------------|
| **ORM** | 用 Python 类代替 SQL 建表和查询 | `models.py` 中的 7 个模型类 |
| **URL 路由** | 把 URL 映射到处理函数 | `urls.py` 中的 37 个路由 |
| **模板引擎** | 动态生成 HTML 页面 | `templates/` 下的 6 个模板 |
| **管理后台** | 自动生成数据库管理界面 | `admin.py` 注册的模型 |
| **用户认证** | 登录、注册、权限管理 | 自定义 `User` 模型 + session 认证 |
| **Migration 系统** | 数据库版本管理 | `migrations/` 下的迁移文件 |

### Django 的 MTV 架构

Django 采用 **MTV（Model-Template-View）** 架构，对应经典的 MVC 模式：

```
用户请求 → URL路由 → View（视图）→ Model（模型）→ 数据库
                         ↓
                     Template（模板）→ HTML 响应 → 返回给用户
```

- **Model（模型）**：定义数据结构，负责数据库交互（相当于 MVC 的 Model）
- **Template（模板）**：定义页面长什么样，负责展示（相当于 MVC 的 View）
- **View（视图）**：处理业务逻辑，连接 Model 和 Template（相当于 MVC 的 Controller）

---

## 二、Django 项目结构

本项目的文件组织遵循 Django 的标准结构：

```
gene-tree/
├── manage.py                 # Django 命令行入口（所有管理命令都通过它执行）
├── project/                  # 项目配置目录
│   ├── __init__.py           # 初始化：安装 PyMySQL 作为 MySQL 驱动
│   ├── settings.py           # 全局配置：数据库、语言、时区、应用注册等
│   ├── urls.py               # 顶层 URL 路由，分发到各 app 的 urls.py
│   └── wsgi.py / asgi.py     # Web 服务器入口
├── app/                      # 应用目录（核心业务逻辑）
│   ├── models.py             # 数据模型（定义数据库表结构）
│   ├── views.py              # 视图函数（处理请求，返回响应）
│   ├── urls.py               # 应用级 URL 路由
│   ├── services.py           # 业务逻辑（SQL 查询、树构建等）
│   ├── admin.py              # 管理后台注册
│   ├── apps.py               # 应用配置
│   └── migrations/           # 数据库迁移文件
│       ├── 0001_initial.py
│       └── 0002_membergenerationcache.py
├── templates/                # HTML 模板
├── static/                   # 静态文件（CSS、JS）
└── scripts/                  # 数据生成脚本（非 Django 标准）
```

### 关键配置文件 `settings.py`

```python
# 数据库配置：使用 MySQL，通过 PyMySQL 驱动
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'gene_tree'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
    }
}

# 使用自定义 User 模型（而非 Django 内置的）
AUTH_USER_MODEL = "app.User"

# 中文 + 上海时区
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
```

### `project/__init__.py` 中的 PyMySQL 初始化

```python
import pymysql
pymysql.install_as_MySQLdb()
```

这行代码让 PyMySQL（纯 Python 实现的 MySQL 驱动）伪装成 MySQLdb（C 实现的驱动），这样 Django 就能用 PyMySQL 连接 MySQL 了。

---

## 三、Model（模型）—— 用 Python 定义数据库表

### 3.1 什么是 ORM

ORM（Object-Relational Mapping，对象关系映射）是 Django 最核心的特性之一。它的意思是：

> **用 Python 类来描述数据库表，用 Python 对象来操作数据库记录，而不用写 SQL。**

对应关系：

| Python 概念 | 数据库概念 |
|------------|-----------|
| 一个 Model 类 | 一张表 |
| 类中的一个字段 | 表中的一列 |
| 一个 Model 实例 | 表中的一行记录 |
| `Model.objects.filter()` | `SELECT ... WHERE ...` |
| `Model.objects.create()` | `INSERT INTO ...` |
| `instance.save()` | `UPDATE ...` |
| `instance.delete()` | `DELETE FROM ...` |

### 3.2 本项目中的模型定义

在 `models.py` 中定义了 7 个模型，对应 MySQL 中的 7 张表：

#### User（用户表）

```python
class User(AbstractUser):
    id = None                                    # 删除 Django 默认的 id 字段
    user_id = models.BigAutoField(primary_key=True)  # 改用自定义主键
    email = models.EmailField(unique=True)        # 邮箱唯一

    class Meta:
        db_table = "user"                         # 指定数据库表名为 user
```

- 继承 `AbstractUser`：获得 Django 内置的用户名、密码、权限等字段
- `id = None`：去掉 Django 默认的 `id` 自增主键
- `BigAutoField(primary_key=True)`：用 `user_id` 作为 64 位自增主键

对应的 MySQL 表结构（简化）：
```sql
CREATE TABLE user (
    user_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(150) NOT NULL UNIQUE,
    password   VARCHAR(128) NOT NULL,
    email      VARCHAR(254) NOT NULL UNIQUE,
    is_staff   TINYINT(1) NOT NULL DEFAULT 0,
    is_active  TINYINT(1) NOT NULL DEFAULT 1,
    ...
);
```

#### Genealogy（族谱表）

```python
class Genealogy(models.Model):
    genealogy_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    surname = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时自动填入当前时间
    created_by = models.ForeignKey(                        # 外键，关联 User
        User, on_delete=models.CASCADE,                    # 级联删除：用户删了，族谱也删
        related_name="created_genealogies"                 # 反向访问名
    )
```

- `ForeignKey`：定义外键关系。`on_delete=models.CASCADE` 表示如果关联的 User 被删除，这条族谱记录也自动删除。
- `related_name="created_genealogies"`：可以通过 `user.created_genealogies.all()` 反向查询该用户创建的所有族谱。

#### Member（成员表）

```python
class Member(models.Model):
    member_id = models.BigAutoField(primary_key=True)
    genealogy = models.ForeignKey(Genealogy, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=100, db_index=True)  # db_index=True 自动建索引
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')])
    birth_year = models.PositiveIntegerField(null=True, blank=True)  # 可为空
    death_year = models.PositiveIntegerField(null=True, blank=True)
    biography = models.TextField(blank=True, default="")

    class Meta:
        db_table = "member"
        indexes = [models.Index(fields=["name"], name="idx_member_name")]  # 额外索引
```

- `choices=[('M', 'Male'), ('F', 'Female')]`：限制字段只能存 'M' 或 'F'
- `null=True`：数据库层面允许 NULL
- `blank=True`：表单验证层面允许为空
- `db_index=True`：Django 自动在该字段上创建 B-tree 索引

#### ParentChild（父子关系表）

```python
class ParentChild(models.Model):
    pk = models.CompositePrimaryKey("parent_id", "child_id")  # 复合主键
    parent = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="children_links")
    child = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="parent_links")
    relation_type = models.CharField(max_length=10, choices=[('father', 'Father'), ('mother', 'Mother')])

    class Meta:
        db_table = "parent_child"
        constraints = [
            models.CheckConstraint(
                check=~Q(parent=models.F("child")),  # parent_id <> child_id
                name="chk_parent_not_self"
            ),
        ]
        indexes = [
            models.Index(fields=["parent"], name="idx_parent"),
            models.Index(fields=["child"], name="idx_child"),
            models.Index(fields=["parent", "child"], name="idx_parent_child"),
        ]
```

- `CompositePrimaryKey`：Django 5.x 新特性，支持复合主键
- `CheckConstraint`：数据库约束，防止 parent_id = child_id（自己是自己的父亲）
- `~Q(...)`：取反，表示 "parent 不能等于 child"

#### Marriage（婚姻关系表）

```python
class Marriage(models.Model):
    marriage_id = models.BigAutoField(primary_key=True)
    spouse1 = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="marriages_as_spouse1")
    spouse2 = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="marriages_as_spouse2")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="active")

    class Meta:
        db_table = "marriage"
        constraints = [
            models.CheckConstraint(
                check=~Q(spouse1=models.F("spouse2")),  # spouse1 <> spouse2
                name="chk_spouse_not_same"
            )
        ]
```

#### GenealogyUser（用户-族谱权限关联表）

```python
class GenealogyUser(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    genealogy_user_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    genealogy = models.ForeignKey(Genealogy, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')

    class Meta:
        db_table = "genealogy_user"
        constraints = [
            models.UniqueConstraint(fields=["user", "genealogy"], name="uq_genealogy_user_user_genealogy")
        ]
```

- `UniqueConstraint(fields=["user", "genealogy"])`：同一用户在同一族谱中只能有一个角色

#### MemberGenerationCache（代际缓存表）

```python
class MemberGenerationCache(models.Model):
    member = models.OneToOneField(
        Member, on_delete=models.CASCADE, primary_key=True,
        db_column="member_id", related_name="generation_cache"
    )
    genealogy = models.ForeignKey(Genealogy, on_delete=models.CASCADE)
    generation = models.PositiveIntegerField()
    computed_at = models.DateTimeField(auto_now=True)  # 每次保存自动更新时间

    class Meta:
        db_table = "member_generation_cache"
        indexes = [
            models.Index(fields=["genealogy", "generation"], name="idx_mgc_genealogy_generation")
        ]
```

- `OneToOneField`：一对一关系，相当于外键 + 唯一约束
- 用途：缓存每个成员的代际编号，避免每次查询都执行昂贵的递归 CTE

### 3.3 字段类型速查

| Django 字段 | MySQL 类型 | 用途 |
|------------|-----------|------|
| `BigAutoField` | `BIGINT AUTO_INCREMENT` | 64 位自增主键 |
| `CharField(max_length=N)` | `VARCHAR(N)` | 短文本 |
| `TextField` | `LONGTEXT` | 长文本（无长度限制） |
| `IntegerField` | `INT` | 整数 |
| `PositiveIntegerField` | `INT UNSIGNED` | 非负整数 |
| `DateField` | `DATE` | 日期 |
| `DateTimeField` | `DATETIME` | 日期时间 |
| `BooleanField` | `TINYINT(1)` | 布尔值 |
| `EmailField` | `VARCHAR(254)` | 邮箱（带格式验证） |
| `ForeignKey` | `BIGINT` + 外键约束 | 多对一关系 |
| `OneToOneField` | `BIGINT` + 外键 + 唯一约束 | 一对一关系 |
| `ManyToManyField` | 中间表 | 多对多关系 |

### 3.4 字段选项速查

| 选项 | 含义 |
|------|------|
| `primary_key=True` | 设为主键 |
| `unique=True` | 唯一约束 |
| `db_index=True` | 自动创建索引 |
| `null=True` | 数据库允许 NULL |
| `blank=True` | 表单验证允许为空 |
| `default=X` | 默认值 |
| `auto_now_add=True` | 创建时自动填入当前时间（只写一次） |
| `auto_now=True` | 每次保存时自动更新为当前时间 |
| `choices=[...]` | 限制可选值 |
| `on_delete=CASCADE` | 关联记录删除时，本记录也删除 |

---

## 四、Migration（迁移）—— 数据库版本管理

### 4.1 什么是 Migration

Migration 是 Django 的 **数据库版本控制系统**，类似于 Git 管理代码版本：

| Git | Django Migration |
|-----|-----------------|
| 代码文件 | models.py |
| `git diff` | `makemigrations`（对比新旧 models.py，生成变更记录） |
| `git commit` | `migrate`（执行变更，更新数据库） |
| `.git/` 目录 | `migrations/` 目录（存储所有历史变更） |
| commit hash | 迁移文件名（0001、0002...） |

### 4.2 `python manage.py migrate` 到底在干什么

一句话：**把 models.py 里定义的 Python 类，翻译成 MySQL 中的建表语句并执行。**

#### 分步拆解

**第一步：你写了 models.py（定义"我要什么表"）**

比如你定义了 Member 类：

```python
class Member(models.Model):
    member_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, db_index=True)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')])
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    death_year = models.PositiveIntegerField(null=True, blank=True)
```

**第二步：`python manage.py makemigrations`（生成"迁移文件"）**

Django 对比你的 models.py 和上一次的状态，自动生成一个 Python 文件，记录"这次改了什么"：

```python
# 0001_initial.py 中对应 Member 的部分
migrations.CreateModel(
    name='Member',
    fields=[
        ('member_id', models.BigAutoField(primary_key=True)),
        ('name', models.CharField(max_length=100, db_index=True)),
        ('gender', models.CharField(max_length=1, choices=[...])),
        ...
    ],
    options={'db_table': 'member'},
),
```

这个文件就是一份 **"数据库变更说明书"**。

**第三步：`python manage.py migrate`（执行迁移）**

Django 读取迁移文件，将其翻译成具体的 SQL 并在数据库上执行。对于 Member 模型，实际执行的 SQL 大致是：

```sql
CREATE TABLE `member` (
    `member_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `gender` VARCHAR(1) NOT NULL,
    `birth_year` UNSIGNED INT NULL,
    `death_year` UNSIGNED INT NULL,
    `biography` LONGTEXT NOT NULL,
    `genealogy_id` BIGINT NOT NULL,
    INDEX `idx_member_name` (`name`),
    FOREIGN KEY (`genealogy_id`) REFERENCES `genealogy`(`genealogy_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.3 本项目的 migrate 执行了什么

运行 `python manage.py migrate` 时，Django 按顺序执行两个迁移文件：

#### 迁移 0001_initial — 创建 6 张表 + 索引 + 约束

| 操作 | 对应 models.py | 生成的 SQL（简化） |
|------|---------------|-------------------|
| `CreateModel('User')` | `class User(AbstractUser)` | `CREATE TABLE user (user_id BIGINT PK, username VARCHAR(150) UNIQUE, password VARCHAR(128), email VARCHAR(254) UNIQUE, ...)` |
| `CreateModel('Genealogy')` | `class Genealogy` | `CREATE TABLE genealogy (genealogy_id BIGINT PK, title VARCHAR(255), surname VARCHAR(100), created_at DATETIME, created_by BIGINT FK→user)` |
| `CreateModel('Member')` | `class Member` | `CREATE TABLE member (member_id BIGINT PK, name VARCHAR(100), gender VARCHAR(1), ...)` |
| `CreateModel('ParentChild')` | `class ParentChild` | `CREATE TABLE parent_child (parent_id BIGINT, child_id BIGINT, relation_type VARCHAR(10), PRIMARY KEY(parent_id, child_id), ...)` |
| `CreateModel('Marriage')` | `class Marriage` | `CREATE TABLE marriage (marriage_id BIGINT PK, spouse1_id BIGINT FK, spouse2_id BIGINT FK, ...)` |
| `CreateModel('GenealogyUser')` | `class GenealogyUser` | `CREATE TABLE genealogy_user (genealogy_user_id BIGINT PK, user_id BIGINT FK, genealogy_id BIGINT FK, role VARCHAR(20), UNIQUE(user_id, genealogy_id))` |
| `AddIndex` | `indexes = [models.Index(...)]` | `CREATE INDEX idx_member_name ON member(name)` |
| `RunSQL` | 原生 SQL 索引 | `CREATE INDEX idx_member_name_prefix ON member(name(10))` |
| `AddConstraint` | `CheckConstraint` | `ALTER TABLE marriage ADD CONSTRAINT chk_spouse_not_same CHECK (spouse1 <> spouse2)` |

#### 迁移 0002_membergenerationcache — 新增 1 张表

| 操作 | 生成的 SQL |
|------|-----------|
| `CreateModel('MemberGenerationCache')` | `CREATE TABLE member_generation_cache (member_id BIGINT PK, genealogy_id BIGINT FK, generation INT UNSIGNED, computed_at DATETIME, INDEX(genealogy_id, generation))` |

### 4.4 Django 如何知道"该执行哪些迁移"

Django 在数据库中维护一张 `django_migrations` 表：

```
+----+-------+-------------------------------+---------------------+
| id | app   | name                          | applied             |
+----+-------+-------------------------------+---------------------+
|  1 | auth  | 0001_initial                  | 2026-05-06 13:00:00 |
|  2 | app   | 0001_initial                  | 2026-05-06 13:00:01 |
|  3 | app   | 0002_membergenerationcache    | 2026-05-09 11:17:00 |
+----+-------+-------------------------------+---------------------+
```

每次执行 `migrate` 时，Django：
1. 查 `django_migrations` 表，看哪些迁移已经执行过
2. 只执行尚未记录的迁移
3. 执行成功后，把迁移名插入 `django_migrations` 表

所以 **migrate 是幂等的**——跑一次和跑十次效果一样，不会重复建表。

### 4.5 如果修改了 models.py 怎么办

比如你给 Member 加了一个字段 `age`：

```
1. 修改 models.py，加上 age = models.IntegerField(null=True)
2. 运行 python manage.py makemigrations
   → 生成 0003_add_age_to_member.py
3. 运行 python manage.py migrate
   → 执行 ALTER TABLE member ADD COLUMN age INT NULL
```

Django 会自动对比新旧 models.py 的差异，生成增量 SQL，而不是重建整张表。

---

## 五、View（视图）—— 处理请求，返回响应

### 5.1 请求处理流程

```
用户在浏览器输入 URL
    ↓
Django 的 URL 路由（urls.py）找到对应的视图函数
    ↓
视图函数（views.py）执行业务逻辑
    ↓ 可能会调用 services.py 中的函数查询数据库
    ↓
返回 HTTP 响应（HTML 页面 或 JSON 数据）
```

### 5.2 本项目中的两种视图

#### 页面视图（渲染 HTML 模板）

```python
def members_page_view(request):
    # 1. 检查登录状态
    if not request.user.is_authenticated:
        return redirect('/login-page')

    # 2. 查询数据（通过 ORM 或 services.py 中的原生 SQL）
    genealogies = Genealogy.objects.filter(...)
    members = Member.objects.filter(...)

    # 3. 渲染模板，返回 HTML
    return render(request, 'members.html', {
        'genealogies': genealogies,
        'members': members,
    })
```

#### API 视图（返回 JSON）

```python
@api_login_required
def members_view(request):
    if request.method == 'GET':
        members = Member.objects.filter(...)
        # 返回 JSON 数据
        return JsonResponse({'members': list(members.values())})

    elif request.method == 'POST':
        # 创建新成员
        member = Member.objects.create(...)
        return JsonResponse({'member_id': member.member_id}, status=201)
```

### 5.3 URL 路由配置

```python
# app/urls.py
urlpatterns = [
    path('members', views.members_view),                    # GET/POST /members
    path('members/<int:member_id>', views.member_detail_view),  # GET/PUT/DELETE /members/123
    path('ancestors/<int:member_id>', views.ancestors_view),
    path('descendants/<int:member_id>', views.descendants_view),
    path('relationship', views.relationship_view),
    ...
]
```

`<int:member_id>` 是 URL 参数，会自动传递给视图函数。

---

## 六、Template（模板）—— 动态生成 HTML

### 6.1 模板语法

Django 模板使用特殊的标签语法：

```html
<!-- 变量输出 -->
<h1>{{ genealogy.title }}</h1>

<!-- 条件判断 -->
{% if user.is_authenticated %}
    <p>欢迎, {{ user.username }}</p>
{% else %}
    <p>请登录</p>
{% endif %}

<!-- 循环 -->
{% for member in members %}
    <tr>
        <td>{{ member.name }}</td>
        <td>{{ member.gender }}</td>
    </tr>
{% endfor %}

<!-- 模板继承 -->
{% extends "base.html" %}
{% block content %}
    <!-- 页面特有内容 -->
{% endblock %}
```

### 6.2 本项目的模板结构

```
templates/
├── base.html              # 基础布局（导航栏、页脚、CSS/JS 引入）
├── login.html             # 登录页（继承 base.html）
├── members.html           # 成员管理页（CRUD 操作）
├── tree.html              # 后代树（懒加载展开）
├── ancestors_tree.html    # 祖先树（父系蓝色、母系粉色）
├── dashboard.html         # 统计仪表盘（饼图、下载按钮）
└── analysis.html          # 分析查询页（6 种查询）
```

所有页面都继承 `base.html`，共享导航栏和样式。

---

## 七、manage.py 常用命令

```bash
# 启动开发服务器
python manage.py runserver

# 数据库迁移
python manage.py makemigrations        # 生成迁移文件
python manage.py migrate               # 执行迁移
python manage.py showmigrations        # 查看迁移状态

# 创建超级管理员
python manage.py createsuperuser

# 进入 Django Shell（交互式 Python 环境，可直接操作数据库）
python manage.py shell

# 收集静态文件（部署时用）
python manage.py collectstatic

# 运行测试
python manage.py test
```

---

## 八、总结

### Django 的核心价值

1. **ORM**：用 Python 代替 SQL，数据库操作更安全、更 Pythonic
2. **Migration**：数据库结构版本化管理，团队协作不怕冲突
3. **MTV 架构**：关注点分离，代码组织清晰
4. **"电池已包含"**：用户认证、管理后台、表单验证、CSRF 防护等开箱即用

### 本项目中的 Django 使用模式

```
models.py      → 定义 7 张表的结构（Python 类）
views.py       → 37 个视图函数，处理 HTTP 请求
services.py    → 1058 行业务逻辑，包含大量原生 SQL（递归 CTE 等 ORM 难以表达的查询）
urls.py        → URL 到视图的映射
templates/     → 6 个 HTML 模板，用 Django 模板语言渲染
migrations/    → 2 个迁移文件，管理数据库结构变更
```

### migrate 的完整流程

```
models.py          你用 Python 描述"要什么表"
      ↓  makemigrations
迁移文件             Django 记录"这次改了什么"
      ↓  migrate
SQL 执行            Django 翻译成 SQL 并在 MySQL 上执行
      ↓
django_migrations   记录"已执行过哪些迁移"
```

**一句话总结：Django = 用 Python 写 Web 应用的全套工具箱，migrate = 把 Python 定义的表结构自动同步到 MySQL 数据库。**
