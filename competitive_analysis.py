import os
import csv
from dashscope import MultiModalConversation
import analysis_config as config
from get_keyword import get_keyword

# 使用通义千问模型获取竞品分析
def get_img_analyze(my_image_path, amazon_image_path):
    # 构建图片路径格式
    my_image_url = f"file://{os.path.abspath(my_image_path)}"
    amazon_image_url = f"file://{os.path.abspath(amazon_image_path)}"
    
    messages = [
        {
            "role": "system",
            "content": [{"text": config.SYSTEM_PROMPT}]
        },
        {
            "role": "user",
            "content": [
                {"image": my_image_url},
                {"image": amazon_image_url},
                {"text": config.USER_PROMPT}
            ]
        }
    ]
    
    response = MultiModalConversation.call(
        api_key=config.API_KEY,
        model=config.MODEL_NAME,
        messages=messages,
        vl_high_resolution_images=True
    )
    
    return get_img_conclusion(response["output"]["choices"][0]["message"]["content"][0]["text"].strip())

# 结论提取
def get_img_conclusion(content):
    conclusion = content.split('\n')[0].split('：')[-1].strip()
    return conclusion

def get_title_analyze(my_words, title):
    for word in my_words.split(' '):
        if word not in title:
            return 'NO'
    return 'YES'

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
                'product_name': get_product_name(file),
                'key_words': get_keyword(config.API_KEY, config.BASE_URL, 'qwen-max-2025-01-25', get_product_name(file))
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
                    img_conclusion = get_img_analyze(my_image['path'], amazon_image['path'])
                    title_conclusion = get_title_analyze(my_image['key_words'], amazon_image['filename'])
                    conclusion = 'YES' if (title_conclusion, img_conclusion) == ('YES', 'YES') else 'NO'
                    if conclusion == 'YES':
                        print('是竞品')
                    else:
                        print('不是竞品')
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