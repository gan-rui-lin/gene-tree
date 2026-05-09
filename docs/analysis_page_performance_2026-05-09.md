# `/analysis-page` 性能优化记录（2026-05-09）

## 1. 问题现象

- 页面请求偏慢：
  - `GET /analysis-page`（优化前）约 `3.39s`，响应体约 `17.98MB`
- 若直接调用分析接口，部分 SQL 明显慢：
  - `fetch_longest_lifespan_generation(3)` 约 `14.8s`
  - `fetch_unmarried_male_over_50(3)` 约 `121.8s`
  - `fetch_early_born_members(3)` 约 `14.7s`

## 2. 排查时执行的关键命令

> 下列命令用于测量页面和服务函数耗时，并验证迁移。

```bash
python manage.py migrate
python manage.py check
```

```bash
python manage.py shell -c "from django.test import Client; import time; c=Client(); t=time.perf_counter(); r=c.get('/analysis-page'); print('status=',r.status_code,'bytes=',len(r.content),'ms=',(time.perf_counter()-t)*1000)"
```

```bash
python manage.py shell -c "import time; from app.services import fetch_longest_lifespan_generation; t=time.perf_counter(); print(fetch_longest_lifespan_generation(3)); print('ms=',(time.perf_counter()-t)*1000)"
```

```bash
python manage.py shell -c "import time; from app.services import fetch_unmarried_male_over_50; t=time.perf_counter(); print(len(fetch_unmarried_male_over_50(3))); print('ms=',(time.perf_counter()-t)*1000)"
```

```bash
python manage.py shell -c "import time; from app.services import fetch_early_born_members; t=time.perf_counter(); print(fetch_early_born_members(3)); print('ms=',(time.perf_counter()-t)*1000)"
```

## 3. SQL / 建模层面的瓶颈分析

1. `/analysis-page` 一次性下发全量成员（大族谱约 5 万人）到前端下拉框，导致页面传输和渲染都重。
2. 代际统计（Q3/Q5）每次都用递归 CTE 临时重算 generation，重复计算成本高。
3. 配偶查询和“未婚男性”查询里使用 `OR` 连接条件，MySQL 难以高效走索引，执行计划膨胀。

## 4. 优化方案与思考

### 4.1 建模增强：引入代际缓存表

- 新增模型与迁移：`member_generation_cache`（迁移：`app.0002_membergenerationcache`）
- 设计目标：
  - 把“成员属于第几代”的结果从“每次递归计算”改成“按族谱缓存复用”
  - 把 CPU 密集/递归开销前置到首次构建，换取后续查询稳定低延迟

### 4.2 SQL 改写：避免 `OR` Join

- `fetch_unmarried_male_over_50`：
  - 由 `LEFT JOIN marriage ON (m.member_id = husband_id OR m.member_id = wife_id)` 改为：
  - 先 `WITH married AS (...)` 汇总所有已婚 member_id，再做 anti-join 过滤未婚
- `fetch_spouse_and_children`：
  - 配偶查询由 `OR` 改为 `UNION ALL` 的两段等值连接，提升索引可用性

### 4.3 页面策略：按族谱按需加载 + 下拉截断

- `analysis_page_view` 只加载当前 `genealogy_id` 数据
- 下拉成员列表限制前 `500` 条，并提供手动输入 member_id
- 把“页面展示可用性”和“大数据全量传输”解耦

## 5. 优化前后对比

| 指标 | 优化前 | 优化后 |
|---|---:|---:|
| `/analysis-page` | ~3390ms, ~17.98MB | ~55ms, ~176KB |
| Q3: 最长寿命代（genealogy_id=3） | ~14.8s | 首次~2.5s（建缓存），后续~0.16-0.27s |
| Q4: 未婚男性>50岁 | ~121.8s | ~0.26s |
| Q5: 每代最早出生 | ~14.7s | ~0.50-0.57s |
| `/analysis/longest-lifespan-generation?genealogy_id=3` | 慢 | ~231ms |

## 6. 取舍与后续建议

- 当前代际缓存使用“按族谱 member 数量变化触发重建”的轻量策略，实现简单、收益高。
- 若后续出现“成员不增减但父子关系变化”的高频编辑场景，建议升级为：
  - 关系表变更时间戳/版本号驱动失效；
  - 或在增删改父子关系时增量维护缓存。
- 仍可继续优化项：
  - 亲缘最短路径 BFS 查询（目前在大数据下仍可能接近秒级）；
  - 给高频过滤字段补充复合索引并结合 `EXPLAIN ANALYZE` 做进一步微调。
