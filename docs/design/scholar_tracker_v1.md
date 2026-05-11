# Scholar-Tracker v1

> QED-Tracker 设计文档。只做检索、分类、索引，不处理内容。

## 检索清单（突破朗道位垒）

| 编号 | 课程 | 目标教材 | 习题集 | 状态 |
|------|------|---------|--------|------|
| 01 | 数学分析 | Rudin *Principles* / Tao *Analysis* | Kaczor 三卷本 / 吉米多维奇 | ✅ 已有 |
| 02 | 线性代数 | Axler *LADR* / Hoffman & Kunze | Zhang Fuzhen / 苏联习题集 | ✅ 已有 |
| 03 | 点集拓扑 | Munkres *Topology* | 课后习题 | 📥 待检索 |
| 04 | 实分析 | Stein *Real Analysis* / Folland | Wheeden | 📥 待检索 |
| 05 | 复分析 | Stein *Complex Analysis* / Ahlfors | 留数练习 | 📥 待检索 |
| 06 | 泛函分析 | Stein *Functional Analysis* / Lax | Saxe | 📥 待检索 |
| 07 | ODE | Tenenbaum *ODE* | 课后习题 | 📥 待检索 |
| 08 | PDE | Evans *PDE* | 课后习题 | 📥 待检索 |
| 09 | 抽象代数 | Dummit & Foote / Aluffi | 课后习题 | 📥 待检索 |
| 10 | QE 冲刺 | — | *Berkeley Problems* | 📥 待检索 |

## 三大采集器

### PaperCollector — arXiv 论文

```
输入: arXiv 分类 (math.CA/FA/AP/CV)
流程: arXiv API 搜索 → 逐篇展示标题+作者+摘要 → [Y/n] 确认
     → httpx 下载 PDF → dataset/papers/{year}/{arxiv_id}_{title}.pdf
     → 写入 PostgreSQL papers 表 (幂等: arxiv_id UNIQUE)
```

### TextbookHunter — 教材 PDF

```
输入: 课程名 + 目标教材名
流程: httpx + bs4 搜索 libgen.is → 结果列表 → 选择下载
     → httpx 流式下载 → dataset/textbooks/{course}/{title}.pdf
     → 写入 PostgreSQL textbooks 表
来源: Library Genesis (libgen.is)
```

### DocScraper — 官方文档

```
输入: 名称 + 官网 URL
流程: wget --mirror --convert-links --page-requisites
     → dataset/official_docs/{name}/ (完整 HTML 结构)
     → 写入 PostgreSQL official_docs 表
目标: PyTorch / scikit-learn / YOLO
```

## 数据集布局

```
dataset/
├── textbooks/
│   ├── 01_math_analysis/      # 3 PDF ✅
│   ├── 02_linear_algebra/     # 2 PDF ✅
│   ├── 03_topology/           # 空
│   ... (至 10_qe_prep)
├── papers/
│   └── {year}/
└── official_docs/
    ├── pytorch/
    ├── scikit_learn/
    └── yolo/
```
