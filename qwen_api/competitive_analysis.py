import os
from openai import OpenAI
import base64
import config

# base64编码图片
def encode_image(image_path: list):
    base64_images = []
    for img in image_path:
        with open(img, "rb") as image_file:
            base64_images.append(base64.b64encode(image_file.read()).decode("utf-8"))
    return base64_images

# 使用通义千问模型获取竞品分析
def get_analyze(image_path):
    result_prompt = '''
                    输出格式如下
                    结论：YES/NO
                    理由：XXXXXX
                    '''
    base64_image = encode_image(image_path)
    client = OpenAI(
        api_key=config.API_KEY,
        base_url=config.BASE_URL,
    )
    completion = client.chat.completions.create(
        model=config.MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": [{"type":"text","text": config.SYSTEM_PROMPT}]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image[0]}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image[1]}"},
                    },
                    {"type": "text", "text": config.USER_PROMPT},
                    {"type": "text", "text": '完成以上所有工作后，得出最终的结论。如果是竞品，就输出YES，如果不是，就输出NO。'},
                    {"type": "text", "text": result_prompt},
                ],
            }
        ],
    )
    return completion.choices[0].message.content.strip()

# 结论提取
def get_conclusion(content):
    conclusion = content.split('\n')[0].split('：')[-1].strip()
    return conclusion

def main():
    img_dir = config.IMAGE_DIRECTORY
    image_paths = []
    files = []
    for file in os.listdir(img_dir):
        if os.path.splitext(file)[1] in config.IMAGE_EXTENSIONS:
            files.append(os.path.join(img_dir, file))
    image_paths.extend(files)
    
    content = get_conclusion(get_analyze(image_paths))
    print(content)

if __name__ == "__main__":
    main() 