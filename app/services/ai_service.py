import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一位专业的日志分析工程师。请根据提供的日志内容进行分析，返回严格的 JSON 格式结果，包含以下字段：

- summary: 日志整体摘要（2-3 句话，概括日志覆盖的时间段、主要活动和整体健康状态）
- causes: 发现的异常原因（逐条列出，每条说明具体错误和相关上下文；如果正常则说明"未发现明显异常"）
- suggestions: 排障建议（针对每个异常给出具体的排查和修复建议；如果正常则给出预防性建议）

只返回 JSON，不要包含其他内容。\
"""


def analyze_log_content(log_content: str) -> dict[str, str]:
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    truncated = log_content[:12000]

    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下日志内容：\n\n{truncated}"},
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(raw[json_start:json_end])
        else:
            logger.warning("Failed to parse AI response as JSON: %s", raw[:200])
            result = {
                "summary": raw,
                "causes": "AI 返回内容无法解析为结构化结果。",
                "suggestions": "请重新尝试分析。",
            }

    def to_str(value):
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value) if value is not None else ""

    return {
        "summary": to_str(result.get("summary", "")),
        "causes": to_str(result.get("causes", "")),
        "suggestions": to_str(result.get("suggestions", "")),
    }
