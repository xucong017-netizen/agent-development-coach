"""课堂用只读课程查询；数据是模拟目录，不调用模型或 LangChain。"""
import json
import sys
from pathlib import Path


def load_catalog() -> dict:
    """读取与本文件放在同一目录的课程 JSON。"""
    path = Path(__file__).with_name("course_catalog.json")
    return json.loads(path.read_text(encoding="utf-8"))


def search_courses(topic: str) -> dict:
    """按主题查询课程；无匹配返回空列表，空主题拒绝查询。"""
    query = topic.strip().casefold()
    if not query:
        raise ValueError("请先提供学习主题。")
    catalog = load_catalog()
    items = [item for item in catalog["items"]
             if query in item["topic"].casefold()]
    return {"items": items, "source": catalog["source"]}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：python tools.py <学习主题>")
    print(json.dumps(search_courses(sys.argv[1]), ensure_ascii=False, indent=2))
