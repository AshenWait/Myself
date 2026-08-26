# 欧奈尔选股程序

这是 `AshenWait/Myself` monorepo 中面向本地通达信数据的 CAN SLIM / 欧奈尔风格选股 CLI，只依赖 Python 标准库。

## 能做什么

- 读取本地通达信日线文件：`vipdoc/sh/lday/*.day`、`vipdoc/sz/lday/*.day`
- 仅对 `60xxxx` 和 `00xxxx` 股票做 0-100 分评分
- 输出排名 CSV / JSON
- 将高分股票自动加入本地自选股 `storage/watchlist.json`
- 将自选股导出为 CSV，方便给前端、脚本或其它服务继续使用

## 评分逻辑

总分由 6 个组件组成：

| 组件 | 权重 | 数据来源 |
| --- | ---: | --- |
| 趋势强度 | 30 | 通达信日线 |
| 相对强弱 / 领涨 | 20 | 通达信日线，按股票池内动量分位 |
| 量能吸筹 | 15 | 通达信日线 |
| 接近新高 / 突破 | 10 | 通达信日线 |
| 市场环境 | 10 | 默认 `sh000001` 指数日线 |
| 基本面 | 15 | 可选 `metadata.csv` |

重要假设：

- 通达信日线稳定支持价格、成交量、成交额，所以技术类评分可信度更高。
- EPS、营收、ROE、机构持仓等不是 `.day` 文件内的数据，必须通过可选 CSV 提供。
- 如果没有基本面 CSV，基本面组件按中性 50 分处理，并在结果 `flags` 中标记 `fundamental_data_missing`。
- 分数是研究优先级，不是买入建议。

## 快速运行

在本目录执行：

```powershell
python -m oneil_screener.cli scan --tdx-root D:\new_tdx64 --auto-add --min-score 75
```

启动本地 API：

```powershell
python -m oneil_screener.api
```

作品集中的“选股”页面通过 `http://127.0.0.1:8765` 读取评分结果、触发扫描并管理自选股。仓库根目录的 `scripts/start-dev.ps1` 会自动启动该 API。

常用参数：

```powershell
python -m oneil_screener.cli scan `
  --tdx-root D:\new_tdx64 `
  --benchmark sh000001 `
  --metadata-csv metadata.example.csv `
  --output output\oneil_scores.csv `
  --json-output output\oneil_scores.json `
  --watchlist storage\watchlist.json `
  --auto-add `
  --min-score 75 `
  --top 50
```

查看自选股：

```powershell
python -m oneil_screener.cli watchlist list --watchlist storage\watchlist.json
```

移除自选股：

```powershell
python -m oneil_screener.cli watchlist remove 600000 --watchlist storage\watchlist.json
```

导出自选股：

```powershell
python -m oneil_screener.cli watchlist export --watchlist storage\watchlist.json --output output\watchlist.csv
```

## 元数据 CSV

可选字段见 `metadata.example.csv`：

| 字段 | 说明 |
| --- | --- |
| `symbol` | 必填，支持 `sh600000` 或 `600000` |
| `name` | 股票名 |
| `industry` | 行业 |
| `eps_yoy` | 最近一期 EPS 同比，百分数 |
| `revenue_yoy` | 最近一期营收同比，百分数 |
| `eps_3y_cagr` | 近三年 EPS CAGR，百分数 |
| `roe` | ROE，百分数 |
| `float_market_cap` | 流通市值，可保留给后续筛选 |
| `institutional_ownership` | 机构持仓比例，可保留给后续筛选 |

## 输出文件

默认输出：

- `output/oneil_scores.csv`：完整评分排名
- `storage/watchlist.json`：自选股持久化文件

`watchlist.json` 保留完整评分、组件分、原因和更新时间。它是运行时数据，已在 `.gitignore` 中忽略。

## 测试

```powershell
$env:PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests -v
```
