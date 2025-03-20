import json
from openai import OpenAI

def get_keyword(api_key, base_url, model, product_name):
    client = OpenAI(
        api_key=api_key, 
        base_url=base_url,
    )
    completion = json.loads(client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': f'真正的产品名是标题的一部分。就是标题有很多其他修饰成分，你要从标题里面提取出关键词。例如“健康饮食，美妙的一天，当当牌轻食罐头，你值得拥有”，那么关键词就是“轻食罐头” 那么"{product_name}"这是商品名字，请问关键词是什么？请你直接输出关键词，而不要输出其他任何东西，任何说明和提示。'}],
        ).model_dump_json())['choices'][0]['message']['content']
    return completion