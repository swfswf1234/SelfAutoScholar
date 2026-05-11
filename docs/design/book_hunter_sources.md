# Book Hunter — 教材检索方案

## 来源

| 源 | 策略 | 方法 |
|----|------|------|
| **Library Genesis** | 主源，覆盖绝大多数数学教材 | httpx + BeautifulSoup 搜索 libgen.is，解析结果表 |

## 待检索课程

| # | 课程 | 英文目标 | 中文目标 |
|---|------|---------|---------|
| 03 | 点集拓扑 | Munkres *Topology* | 熊金城《点集拓扑》 |
| 04 | 实分析 | Stein *Real Analysis* / Folland | 周民强《实变函数论》 |
| 05 | 复分析 | Stein *Complex Analysis* / Ahlfors | — |
| 06 | 泛函分析 | Stein *Functional Analysis* / Lax | 张恭庆《泛函分析》 |
| 07 | ODE | Tenenbaum *ODE* | 丁同仁《常微分方程》 |
| 08 | PDE | Evans *PDE* | — |
| 09 | 抽象代数 | Dummit & Foote / Aluffi | — |
| 10 | QE 冲刺 | *Berkeley Problems* | — |

## 搜索逻辑

```
LibGenHunter.search("Munkres Topology")
  → GET https://libgen.is/search.php?req=Munkres+Topology
  → parse <table class="c"> rows
  → extract: title, author, year, language, size, download_url
  → filter: ext == "pdf"
  → sort: language=zh first, year desc
  → return list[dict]
```

## 下载逻辑

```
LibGenHunter.download(url, save_path)
  → GET download_url (follow redirects)
  → if redirected to library.lol or .pdf: download content
  → write to save_path
```
