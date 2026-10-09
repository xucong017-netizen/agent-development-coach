"""最小闭环：一个输入、一个处理节点、一个可观察输出。"""
def respond(state, context):
    """framework 用模拟回答验证真实图；real 调用环境中配置的模型。"""
    if context['mode'] == 'real':
        import os
        from langchain_openai import ChatOpenAI
        reply = ChatOpenAI(model=os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'), timeout=25, max_retries=0).invoke(state['question'])
        return {'answer': str(reply.content)}
    return {'answer': '【模拟模型，真实框架】已收到：' + str(state['question'])}
