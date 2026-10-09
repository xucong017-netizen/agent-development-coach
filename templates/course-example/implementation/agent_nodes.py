"""课程咨询的真实节点。框架模式用模拟回答，real 模式调用真实模型。"""
import json
from tools import search_courses

def validate_request(state, context):
    """接收问题，提取主题并区分缺参、越界和正常请求。"""
    question = state.get('question', '')
    if not isinstance(question, str): return {'topic': '', 'route': 'invalid'}
    topic = question.strip()
    if not topic: return {'topic': '', 'route': 'missing'}
    if any(word in topic for word in ('转账', '天气', '删除文件')): return {'topic': topic, 'route': 'outside'}
    return {'topic': topic, 'route': 'search'}

def ask_topic(state, context):
    """缺少主题时，明确请求补充，而不是猜测。"""
    return {'answer': '请告诉我你想学习的课程主题。'}

def search_catalog(state, context):
    """调用项目真实工具；捕获失败，提供明确失败状态供图路由。"""
    try:
        result = search_courses(state['topic'])
        return {'documents': result['items'], 'source': result['source'], 'error': ''}
    except Exception as error:
        return {'documents': [], 'source': '', 'error': str(error)}

def answer_courses(state, context):
    """有资料才回答；两种模型模式清楚分开。"""
    if context['mode'] == 'real':
        from langchain_openai import ChatOpenAI
        import os
        model = ChatOpenAI(model=os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'), timeout=25, max_retries=0)
        reply = model.invoke('你是课程咨询助手。仅根据以下资料回答，不编造。问题：' + state['question']
                             + '\n资料：' + json.dumps(state['documents'], ensure_ascii=False))
        return {'answer': str(reply.content)}
    return {'answer': '【模拟模型】找到课程：' + json.dumps(state['documents'], ensure_ascii=False)}

def tool_error(state, context):
    """工具失败独立出口，避免宣称查询成功。"""
    return {'answer': '课程查询失败，请稍后重试。'}

def no_result(state, context):
    """没有资料时如实回应。"""
    return {'answer': '未找到该主题课程，请换一个主题。'}

def invalid_request(state, context):
    """类型错误不进入工具。"""
    return {'answer': '问题必须是文字。'}

def outside_scope(state, context):
    """本任务只做课程咨询。"""
    return {'answer': '我只能提供课程咨询，无法处理这个任务。'}

def agent_model(state, context):
    """动态路线：模型返回工具调用或最终回答；保存公开消息，不展示私有推理。"""
    from langchain_core.messages import AIMessage, HumanMessage, messages_to_dict, messages_from_dict
    messages = messages_from_dict(state.get('messages', []))
    if not messages: messages = [HumanMessage(content=state['question'])]
    attempts = state.get('attempts', 0) + 1
    if attempts >= 3:
        reply = AIMessage(content='已达到模型调用上限，结束本次任务。')
    elif context['mode'] == 'real':
        import os
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(model=os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'), timeout=25, max_retries=0)
        reply = model.bind_tools([search_courses]).invoke(messages)
    elif messages[-1].type == 'tool':
        reply = AIMessage(content='【模拟模型】根据工具结果回答：' + str(messages[-1].content))
    elif not state['question'].strip():
        reply = AIMessage(content='请补充课程主题。')
    elif any(word in state['question'] for word in ('转账', '天气', '删除文件')):
        reply = AIMessage(content='我只能提供课程咨询。')
    else:
        reply = AIMessage(content='', tool_calls=[{'name': 'search_courses', 'args': {'topic': state['question']}, 'id': 'course_' + str(attempts), 'type': 'tool_call'}])
    messages.append(reply)
    return {'messages': messages_to_dict(messages), 'attempts': attempts,
            'choice': 'tools' if reply.tool_calls else 'finish', 'answer': str(reply.content)}

def agent_tools(state, context):
    """按模型公开 tool_calls 调用允许的工具；ToolMessage 对齐调用 ID。"""
    from langchain_core.messages import ToolMessage, messages_to_dict, messages_from_dict
    messages = messages_from_dict(state['messages'])
    for call in messages[-1].tool_calls:
        try:
            if call['name'] != 'search_courses': raise ValueError('不允许的工具')
            value = search_courses(**call['args'])
        except Exception as error:
            value = {'error': str(error)}
        messages.append(ToolMessage(content=json.dumps(value, ensure_ascii=False), tool_call_id=call['id']))
    return {'messages': messages_to_dict(messages), 'tool_steps': state.get('tool_steps', 0) + 1}
