# Northbound Mutual Fund AUM Tracker

这个仓库用于每周一或手动触发，访问北上互认基金管理人的官网页面，抽取基金规模数据，并把不同币种按运行当天的最新汇率换算成美元。

## 功能

- 从 `data/northbound_mutual_funds_20260427.json` 读取附件里的基金名单。
- 按 `config/manager_sources.json` 中配置的管理人官网入口抓取 HTML/PDF 文本，优先发现最新财务报表、年报、中报和审计/未审计报告。
- 识别基金总规模和内地销售份额规模相关金额。
- 使用 Frankfurter 汇率接口获取当天汇率，转换成美元。
- 输出 JSON 和 CSV 到 `outputs/`，并在 GitHub Actions 中自动提交结果。
- 支持 GitHub Actions `workflow_dispatch` 手动运行和每周一定时运行。

## 本地运行

```bash
python -m pip install -e ".[dev]"
northbound-aum-tracker \
  --fund-data data/northbound_mutual_funds_20260427.json \
  --sources config/manager_sources.json \
  --output-dir outputs
```

只跑部分管理人：

```bash
northbound-aum-tracker --manager "摩根基金(亚洲)" --manager "汇丰投资基金(香港)"
```

## 配置说明

`config/manager_sources.json` 是最重要的配置文件。每个管理人需要维护：

- `official_site`: 管理人官网。
- `seed_urls`: 抓取入口页，建议填基金列表页、基金详情页、月报或 factsheet 页面。
- `discover_links`: 是否从入口页继续发现基金、factsheet、monthly report、NAV 等相关链接。
- `max_discovered_links`: 每个管理人最多继续抓取多少个发现链接。

官网格式差异很大，通用提取器会输出证据和失败原因。对于抽取不到的管理人，优先补充更精确的 `seed_urls`，尤其是“Fund documents / Reports / Financial reports / Annual reports”页面。

很多北上互认基金不会在普通基金详情页直接披露内地销售份额规模。本项目的默认抓取顺序是：

1. 最新 financial statements / annual report / interim report PDF
2. 月报或 factsheet
3. 基金详情页

财报中常见的 `US$'000`、`HK$'000`、`in thousands of US dollars` 等表格单位会按千元换算后再转成美元。

## 输出

每次运行会生成：

- `outputs/northbound_aum_YYYY-MM-DD.json`
- `outputs/northbound_aum_YYYY-MM-DD.csv`
- `outputs/northbound_aum_YYYY-MM-DD.xlsx`
- `outputs/latest.json`
- `outputs/latest.csv`
- `outputs/latest.xlsx`

`latest.xlsx` 是主要查看文件。它保留附件原来的两张表，并在 `基金规模合计(亿人民币)` 后插入 `最新基金规模合计(亿人民币）（YYYY-MM-DD）`。如果最新值与原表规模不同，该单元格会标红；如果没有抓到官网/财报证据，单元格留空并带批注说明抓取情况。

JSON 中每条金额都包含：

- 原币种金额
- 美元金额
- 使用汇率
- 来源 URL
- 命中的上下文片段

## GitHub Actions

`.github/workflows/northbound-aum-tracker.yml` 提供：

- 手动触发：Actions 页面点击 `Run workflow`
- 定时触发：每周一北京时间 09:10，UTC 时间 01:10

工作流会运行爬虫并提交 `outputs/` 的变化。
