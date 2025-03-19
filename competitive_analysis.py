import os
import csv
from openai import OpenAI
import base64
import analysis_config as config

# base64编码图片
def encode_image(image_path: list):
    base64_images = []
    for img in image_path:
        with open(img, "rb") as image_file:
            base64_images.append(base64.b64encode(image_file.read()).decode("utf-8"))
    return base64_images

# 使用通义千问模型获取竞品分析
def get_analyze(my_image_path, amazon_image_path):
    result_prompt = '''
    输出格式如下
    结论：YES/NO
    理由：XXXXXX
    '''
    base64_images = encode_image([my_image_path, amazon_image_path])
    
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
                        "image_url": {"url": f"data:image/png;base64,{base64_images[0]}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_images[1]}"},
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

# 从文件名中提取商品名称（去掉扩展名）
def get_product_name(filename):
    return os.path.splitext(filename)[0]

def main():
    # 获取我的商品图片路径及名称
    my_images = []
    for file in os.listdir(config.MY_IMAGE_DIRECTORY):
        if os.path.splitext(file)[1] in config.IMAGE_EXTENSIONS:
            my_images.append({
                'path': os.path.join(config.MY_IMAGE_DIRECTORY, file),
                'filename': file,
                'product_name': get_product_name(file)
            })
    
    # 创建CSV文件
    with open('comparison_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 写入结果
        for my_image in my_images:
            product_name = my_image['product_name']
            product_dir = os.path.join(config.AMAZON_IMAGE_DIRECTORY, product_name)
            
            # 检查亚马逊目录中是否存在对应商品名称的文件夹
            if not os.path.exists(product_dir) or not os.path.isdir(product_dir):
                print(f"警告: 在亚马逊目录中找不到匹配的商品目录: {product_name}")
                continue
            
            # 获取该商品目录下的所有产品图片
            amazon_images = []
            for file in os.listdir(product_dir):
                if os.path.splitext(file)[1] in config.IMAGE_EXTENSIONS:
                    amazon_images.append({
                        'path': os.path.join(product_dir, file),
                        'filename': file
                    })
            
            # 构建这个商品的标题行
            header = [f"我的商品\\亚马逊商品: {product_name}"]
            for amazon_image in amazon_images:
                header.append(amazon_image['filename'])
            
            writer.writerow(header)
            
            # 写入对比结果行
            row = [my_image['filename']]
            
            for amazon_image in amazon_images:
                print(f"对比: {my_image['filename']} vs {product_name}/{amazon_image['filename']}")
                
                try:
                    content = get_analyze(my_image['path'], amazon_image['path'])
                    conclusion = get_conclusion(content)
                    row.append(conclusion)
                except Exception as e:
                    print(f"错误: {str(e)}")
                    row.append("ERROR")
            
            writer.writerow(row)
            # 添加一个空行分隔不同商品
            writer.writerow([])
    
    print(f"结果已保存到 comparison_results.csv")

if __name__ == "__main__":
    main()