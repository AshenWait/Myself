# Week 9 评测和检索优化报告

## 目标

第 9 周的目标是把 RAG 效果从“感觉还可以”变成可复查的评测流程。

当前评测链路：

```txt
eval/questions.json
-> eval/run_rag_eval.py
-> eval/results.json
-> eval/analyze_results.py
-> eval/report.json
-> eval/analyze_citations.py
-> eval/citation_report.json
-> eval/analyze_failures.py
-> docs/week9-failure-analysis.md
-> eval/compare_optimization.py
-> eval/optimization_report.json
```

## 指标来源

这些指标必须来自脚本输出，不能手动拍脑袋填写：

| 指标 | 来源文件 | 说明 |
| --- | --- | --- |
| top-3 检索命中率 | `eval/report.json` | 标准来源是否出现在前 3 个 sources 中 |
| 引用完整率 | `eval/citation_report.json` | 成功回答是否带 sources |
| 失败原因分类 | `eval/failure_analysis.json` | 把失败归类为切分、检索、prompt、幻觉、文档缺失 |
| 参数前后对比 | `eval/optimization_report.json` | 比较同一批题在不同参数下的指标变化 |

## Day 59：top-3 检索命中率

`eval/analyze_results.py` 会检查每条评测结果的前 3 个 sources，判断标准文档和标准页码是否出现在里面。

```txt
标准来源：tests/fixtures/sample.txt 第 1 页
实际 sources 前 3 条：sample.txt 第 1 页、sample.md 第 1 页、sample.pdf 第 1 页
结果：top-3 命中
```

这个指标回答的是：系统有没有把正确资料检索回来。

## Day 60：引用完整率

`eval/analyze_citations.py` 会检查每条成功回答是否带 sources。

```txt
status = success
sources = []
结果：missing_sources
```

这个指标回答的是：最终回答是否可追溯。如果成功回答没有引用来源，就应该继续保留输出检查，必要时强化 prompt。

## Day 61：失败原因分类

`eval/analyze_failures.py` 会把低质量结果分成 5 类：

| 分类 | 含义 | 常见处理 |
| --- | --- | --- |
| 切分问题 | 文档对了，但页码或 chunk 边界不对 | 调整 `rag_chunk_size` 或 `rag_chunk_overlap` |
| 检索问题 | top-k 没有返回正确文档 | 调整 `rag_top_k` 或 `max_rag_distance` |
| prompt 问题 | 来源命中，但回答没有答到标准答案 | 修改 RAG prompt |
| 模型幻觉 | 没有来源却给出确定性回答 | 加强输出检查 |
| 文档缺失 | 文档没有上传、解析或入库 | 检查文档导入和 embedding |

## Day 62：参数优化方式

当前参数基线：

```txt
rag_chunk_size = 500
rag_chunk_overlap = 50
rag_top_k = 3
max_rag_distance = 0.8
```

候选实验参数：

```txt
rag_chunk_size = 700
rag_chunk_overlap = 80
rag_top_k = 5
max_rag_distance = 0.85
```

注意：候选参数不是结论。它只是下一轮实验配置。是否更好，要用同一批 `eval/questions.json` 跑前后对比。

推荐实验步骤：

```powershell
python eval/run_rag_eval.py --output eval/results.before.json
python eval/analyze_results.py --results eval/results.before.json --output eval/report.before.json

# 修改 .env 中的 RAG_CHUNK_SIZE / RAG_CHUNK_OVERLAP / RAG_TOP_K / MAX_RAG_DISTANCE
# 重新上传文档或重建 chunks 与 embedding

python eval/run_rag_eval.py --output eval/results.after.json
python eval/analyze_results.py --results eval/results.after.json --output eval/report.after.json
python eval/compare_optimization.py
```

## 为什么指标不是拍脑袋

因为每个指标都能追溯到具体数据：

```txt
一道题的标准来源
-> eval/questions.json
模型实际返回来源
-> eval/results.json
命中或未命中
-> eval/report.json
引用完整率
-> eval/citation_report.json
失败原因
-> eval/failure_analysis.json
参数前后变化
-> eval/optimization_report.json
```

如果某个指标变好，需要能指出是哪一批题、哪次参数、哪个报告文件证明的。

## 面试表达

我给 RAG 系统建立了离线评测流程。先用 `eval/questions.json` 固定评测题和标准来源，再批量调用 RAG 接口保存结果。之后脚本会计算 top-3 命中率、引用完整率，并把失败分成切分问题、检索问题、prompt 问题、模型幻觉和文档缺失。参数优化不是凭感觉改，而是用同一批题对比 before/after 指标。
