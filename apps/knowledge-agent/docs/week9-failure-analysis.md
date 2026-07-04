# Week 9 Day 61 失败分析表

这个文件是失败分析表的落地位置。真实评测完成后，运行下面命令会用实际结果覆盖本文件：

```powershell
python eval/analyze_failures.py
```

生成逻辑：

```txt
eval/results.json
-> eval/analyze_failures.py
-> eval/failure_analysis.json
-> docs/week9-failure-analysis.md
```

表格字段：

| ID | 问题 | 分类 | 原因 | 标准来源 | top 来源 | 建议动作 |
| --- | --- | --- | --- | --- | --- | --- |

分类范围：

| 分类 | 含义 |
| --- | --- |
| 切分问题 | 命中了标准文档，但页码或 chunk 边界不匹配 |
| 检索问题 | top-k 来源没有命中标准文档 |
| prompt 问题 | 来源命中，但回答没有覆盖标准答案关键词 |
| 模型幻觉 | 有确定性回答，但 sources 为空 |
| 文档缺失 | 文档没有上传、解析、入库或生成 embedding |

注意：这里的表格不手工填指标。真实行数据必须由 `eval/analyze_failures.py` 根据 `eval/results.json` 生成。
