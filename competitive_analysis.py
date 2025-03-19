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

def main():
    # 获取我的商品图片路径
    my_images = []
    for file in os.listdir(config.MY_IMAGE_DIRECTORY):
        if os.path.splitext(file)[1] in config.IMAGE_EXTENSIONS:
            my_images.append(os.path.join(config.MY_IMAGE_DIRECTORY, file))
    
    # 获取亚马逊商品目录及图片
    amazon_products = {}
    for product_dir in os.listdir(config.AMAZON_IMAGE_DIRECTORY):
        product_path = os.path.join(config.AMAZON_IMAGE_DIRECTORY, product_dir)
        if os.path.isdir(product_path):
            amazon_products[product_dir] = []
            for file in os.listdir(product_path):
                if os.path.splitext(file)[1] in config.IMAGE_EXTENSIONS:
                    amazon_products[product_dir].append(os.path.join(product_path, file))
    
    # 创建CSV文件
    with open('comparison_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 构建标题行
        header = ['我的商品\\亚马逊商品']
        for product_name, product_images in amazon_products.items():
            for image in product_images:
                image_name = os.path.basename(image)
                header.append(f"{product_name}/{image_name}")
        
        writer.writerow(header)
        
        # 写入每行数据
        for my_image in my_images:
            my_image_name = os.path.basename(my_image)
            row = [my_image_name]
            
            for product_name, product_images in amazon_products.items():
                for amazon_image in product_images:
                    print(f"对比: {my_image_name} vs {product_name}/{os.path.basename(amazon_image)}")
                    
                    try:
                        content = get_analyze(my_image, amazon_image)
                        conclusion = get_conclusion(content)
                        row.append(conclusion)
                    except Exception as e:
                        print(f"错误: {str(e)}")
                        row.append("ERROR")
            
            writer.writerow(row)
    
    print(f"结果已保存到 comparison_results.csv")

if __name__ == "__main__":
    main()