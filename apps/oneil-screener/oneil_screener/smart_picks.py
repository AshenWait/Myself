from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import PriceBar, ScoreResult
from .tdx import find_day_file, normalize_symbol, read_day_file
from .tushare_data import load_sqlite_series


class SmartPicker(Protocol):
    model_name: str

    def select(self, candidates: list[ScoreResult], tdx_root: Path | None) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    base_url: str
    model: str


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_llm_config(app_root: Path) -> LlmConfig:
    file_values: dict[str, str] = {}
    file_values.update(_read_env_file(app_root.parent / "knowledge-agent" / ".env"))
    file_values.update(_read_env_file(app_root / ".env"))

    def setting(name: str, fallback: str = "") -> str:
        return os.environ.get(name) or file_values.get(name) or fallback

    api_key = setting("ONEIL_LLM_API_KEY") or setting("DEEPSEEK_API_KEY")
    if not api_key or api_key.startswith("replace-with") or "你的" in api_key:
        raise ValueError(
            "未配置智选模型密钥，请在 apps/oneil-screener/.env 中设置 ONEIL_LLM_API_KEY，"
            "或配置 apps/knowledge-agent/.env 的 DEEPSEEK_API_KEY"
        )

    return LlmConfig(
        api_key=api_key,
        base_url=setting("ONEIL_LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        model=setting("ONEIL_LLM_MODEL", "deepseek-v4-pro"),
    )


def _round(value: float) -> float:
    return round(float(value), 2)


def _pct_change(current: float, previous: float) -> float:
    return _round((current / previous - 1) * 100) if previous else 0.0


def _technical_snapshot(bars: list[PriceBar]) -> dict[str, Any]:
    if not bars:
        return {}

    closes = [bar.close for bar in bars]
    recent_20 = bars[-20:]
    recent_10 = bars[-10:]
    recent_5 = bars[-5:]
    true_ranges = [
        max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close))
        for previous, current in zip(bars[-15:-1], bars[-14:])
    ]
    prior_volume = [bar.volume for bar in bars[-20:-5]]
    recent_volume = [bar.volume for bar in recent_5]

    return {
        "ma5": _round(mean(closes[-5:])),
        "ma10": _round(mean(closes[-10:])),
        "ma20": _round(mean(closes[-20:])),
        "return_5d_pct": _pct_change(closes[-1], closes[-6]) if len(closes) >= 6 else 0.0,
        "return_10d_pct": _pct_change(closes[-1], closes[-11]) if len(closes) >= 11 else 0.0,
        "support_10d": _round(min(bar.low for bar in recent_10)),
        "resistance_20d": _round(max(bar.high for bar in recent_20)),
        "atr14": _round(mean(true_ranges)) if true_ranges else 0.0,
        "volume_ratio_5_to_prior15": _round(mean(recent_volume) / mean(prior_volume)) if prior_volume else 0.0,
    }


def _candidate_payload(result: ScoreResult, data_path: Path | None) -> dict[str, Any]:
    technicals: dict[str, Any] = {}
    if data_path is not None:
        try:
            if data_path.suffix == ".sqlite3":
                series = load_sqlite_series(data_path, result.symbol)
            else:
                series = read_day_file(find_day_file(data_path, result.symbol), result.symbol, max_records=260)
            technicals = _technical_snapshot(series.bars)
        except FileNotFoundError:
            pass

    return {
        "rank": result.rank,
        "symbol": result.symbol,
        "name": result.name,
        "trade_date": result.trade_date,
        "close": result.close,
        "score": result.score,
        "components": result.components,
        "metrics": result.metrics,
        "reasons": result.reasons,
        "technicals": technicals,
    }


class DeepSeekSmartPicker:
    def __init__(self, app_root: Path):
        self.app_root = app_root
        self.model_name = "deepseek-v4-pro"

    def select(self, candidates: list[ScoreResult], tdx_root: Path | None) -> dict[str, Any]:
        config = load_llm_config(self.app_root)
        self.model_name = config.model
        candidate_data = [_candidate_payload(item, tdx_root) for item in candidates]
        system_prompt = """
你是谨慎的 A 股短线研究助手。只能使用用户提供的通达信日线和欧奈尔评分摘要，不能声称获取了未提供的新闻、公告、实时盘中价格或基本面。
从候选前 10 名中选择恰好 3 只，期限为 3-10 个交易日。给出条件式研究计划，不得保证收益，不得自动执行交易。
价格必须满足：entry_low <= entry_high，stop_loss < entry_low，take_profit_1 > entry_high，take_profit_2 >= take_profit_1。
请输出 JSON 对象，格式如下：
{
  "market_view": "对本批候选的简短判断",
  "selection_logic": "选择这 3 只的共同逻辑",
  "picks": [
    {
      "symbol": "sh600000",
      "confidence": 80,
      "holding_period": "3-10个交易日",
      "entry_low": 10.00,
      "entry_high": 10.20,
      "stop_loss": 9.50,
      "take_profit_1": 11.00,
      "take_profit_2": 11.60,
      "thesis": "入选理由",
      "entry_logic": "触发买入区间的条件",
      "stop_logic": "止损触发逻辑",
      "take_profit_logic": "分批止盈逻辑",
      "risks": ["主要失效风险"]
    }
  ]
}
只输出 JSON，不要输出 Markdown。
""".strip()
        request_payload = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "请分析以下候选数据并输出 json：\n"
                    + json.dumps(candidate_data, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "max_tokens": 3000,
        }
        request = Request(
            f"{config.base_url}/chat/completions",
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"大模型调用失败 (HTTP {error.code}): {detail}") from error
        except URLError as error:
            raise RuntimeError(f"无法连接智选模型服务: {error.reason}") from error

        try:
            content = response_payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("大模型未返回有效的智选 JSON，请重试") from error


def _number(item: dict[str, Any], field: str) -> float:
    try:
        value = float(item[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"智选结果缺少有效价格字段: {field}") from error
    if value <= 0:
        raise ValueError(f"智选价格必须大于 0: {field}")
    return _round(value)


def _text(item: dict[str, Any], field: str) -> str:
    value = str(item.get(field) or "").strip()
    if not value:
        raise ValueError(f"智选结果缺少说明字段: {field}")
    return value[:500]


def _confidence(item: dict[str, Any]) -> int:
    try:
        value = int(float(item.get("confidence", 0)))
    except (TypeError, ValueError) as error:
        raise ValueError("智选结果缺少有效置信度") from error
    return max(0, min(100, value))


def finalize_smart_picks(
    raw: dict[str, Any], candidates: list[ScoreResult], model_name: str
) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("picks"), list) or len(raw["picks"]) != 3:
        raise ValueError("大模型必须从前 10 名中返回恰好 3 只智选股票")

    allowed = {item.symbol: item for item in candidates[:10]}
    seen: set[str] = set()
    picks: list[dict[str, Any]] = []
    for rank, raw_pick in enumerate(raw["picks"], start=1):
        if not isinstance(raw_pick, dict):
            raise ValueError("智选股票格式无效")
        symbol = normalize_symbol(str(raw_pick.get("symbol") or ""))
        if symbol not in allowed:
            raise ValueError(f"智选股票不在扫描前 10 名中: {symbol}")
        if symbol in seen:
            raise ValueError(f"智选股票重复: {symbol}")
        seen.add(symbol)

        candidate = allowed[symbol]
        entry_low = _number(raw_pick, "entry_low")
        entry_high = _number(raw_pick, "entry_high")
        stop_loss = _number(raw_pick, "stop_loss")
        take_profit_1 = _number(raw_pick, "take_profit_1")
        take_profit_2 = _number(raw_pick, "take_profit_2")
        if not entry_low <= entry_high:
            raise ValueError(f"智选买入区间无效: {symbol}")
        if not stop_loss < entry_low:
            raise ValueError(f"智选止损价必须低于买入区间: {symbol}")
        if not entry_high < take_profit_1 <= take_profit_2:
            raise ValueError(f"智选止盈价必须高于买入区间且依次上升: {symbol}")
        if not candidate.close * 0.75 <= entry_low <= entry_high <= candidate.close * 1.25:
            raise ValueError(f"智选买入价偏离最新收盘价过大: {symbol}")
        if stop_loss < candidate.close * 0.7 or take_profit_2 > candidate.close * 1.5:
            raise ValueError(f"智选止盈止损价格偏离最新收盘价过大: {symbol}")

        risks = [str(value).strip()[:200] for value in raw_pick.get("risks", []) if str(value).strip()]
        if not risks:
            raise ValueError(f"智选结果缺少风险说明: {symbol}")
        picks.append(
            {
                "rank": rank,
                "symbol": symbol,
                "name": candidate.name,
                "source_rank": candidate.rank,
                "score": candidate.score,
                "trade_date": candidate.trade_date,
                "close": candidate.close,
                "confidence": _confidence(raw_pick),
                "holding_period": _text(raw_pick, "holding_period"),
                "entry_low": entry_low,
                "entry_high": entry_high,
                "stop_loss": stop_loss,
                "take_profit_1": take_profit_1,
                "take_profit_2": take_profit_2,
                "thesis": _text(raw_pick, "thesis"),
                "entry_logic": _text(raw_pick, "entry_logic"),
                "stop_logic": _text(raw_pick, "stop_logic"),
                "take_profit_logic": _text(raw_pick, "take_profit_logic"),
                "risks": risks[:4],
            }
        )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": model_name,
        "source_trade_date": max(item.trade_date for item in candidates[:10]),
        "candidate_count": min(10, len(candidates)),
        "market_view": str(raw.get("market_view") or "仅基于本批技术数据的短线筛选").strip()[:500],
        "selection_logic": str(raw.get("selection_logic") or "综合评分、趋势、量能与风险收益筛选").strip()[:500],
        "picks": picks,
        "disclaimer": "智选仅基于扫描数据和模型推理，用于研究参考，不构成投资建议或收益承诺。",
    }


def empty_smart_picks() -> dict[str, Any]:
    return {
        "generated_at": None,
        "model": "",
        "source_trade_date": None,
        "candidate_count": 0,
        "market_view": "",
        "selection_logic": "",
        "picks": [],
        "disclaimer": "智选仅用于研究参考，不构成投资建议或收益承诺。",
    }


def load_smart_picks(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_smart_picks()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("picks"), list):
        raise ValueError("Smart picks JSON must contain a picks list")
    return payload


def write_smart_picks(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
