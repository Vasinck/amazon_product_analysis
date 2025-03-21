import os
import time
import random
import json
import pandas as pd
import requests
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    WebDriverException,
    StaleElementReferenceException
)
from openai import OpenAI
from dashscope import MultiModalConversation

#####################################
# 配置参数
#####################################

# 通义千问API配置
API_KEY = 'xxx'
BASE_URL = 'xxx'
MODEL_NAME = 'qwen2.5-vl-72b-instruct'  # 'qvq-72b-preview'

# 图片目录配置
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
AMAZON_IMAGE_DIRECTORY = './images'
MY_IMAGE_DIRECTORY = './my_product_images'

# 标注提示配置
SYSTEM_PROMPT = "You are a helpful assistant."
USER_PROMPT = '''
# Role: 竞品分析专家

## 核心任务
通过分析两张商品图片的关键特征，判断是否为存在竞争关系的同类商品，需特别关注材质差异的否决性原则。

## 处理流程

1. **特征提取阶段**
   - 视觉分析：商品类别、核心功能、外观设计、品牌标识
   - 材质判定：材质类型、材质纹理
   - 属性分析：使用场景、目标人群

2. **竞品判断标准**
   - 第一否决项：材质类型不同 → 立即判定为非竞品；第二否决项：形状不同 → 立即判定为非竞品；第三否决项：灯泡不一样 → 立即判定为非竞品；
   - 核心竞争要素（材质形状灯泡相同时需满足至少两项）：
     ✔️ 同类功能/用途
     ✔️ 重合的目标消费群体
     ✔️ 可替代使用场景

3. **输出规范**
   - 结论格式：【竞品/非竞品】+ 核心判定依据
   - 需包含：
     • 材质比对结论
     • 形状比对结论
     • 灯泡比对结论
     • 其他关键相似特征（若为竞品）
     • 主要差异点（若为非竞品）
   - 置信度标注：对材质判断的确定性分级（高/中/低）

## 特殊处理原则
⚠️ 当出现以下情况时要求补充信息：
- 材质存在复合结构难以判定主要成分
- 商品存在多功能属性导致用途不明确
- 出现新兴材质类型需要具体参数确认

强化人设：你会对竞品的标准更加严格。
输出格式如下
结论：YES/NO
理由：XXXXXX
'''

# 备用用户代理列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36',
]

#####################################
# 辅助函数
#####################################

def get_random_user_agent():
    """获取随机用户代理"""
    return random.choice(USER_AGENTS)

def random_sleep(min_seconds=1, max_seconds=3):
    """随机睡眠一段时间"""
    sleep_time = random.uniform(min_seconds, max_seconds)
    time.sleep(sleep_time)

def get_keyword(api_key, base_url, model, product_name):
    """从产品名称中提取关键词"""
    client = OpenAI(
        api_key=api_key, 
        base_url=base_url,
    )
    completion = json.loads(client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': f'真正的产品名是标题的一部分。就是标题有很多其他修饰成分，你要从标题里面提取出关键词。例如"健康饮食，美妙的一天，当当牌轻食罐头，你值得拥有"，那么关键词就是"轻食罐头" 那么"{product_name}"这是商品名字，请问关键词是什么？请你直接输出关键词，而不要输出其他任何东西，任何说明和提示。'}],
        ).model_dump_json())['choices'][0]['message']['content']
    return completion

def extract_my_product_name(file_path, save_to_file=False, output_file="流量词列表.txt"):
    """从Excel文件中提取第一列(流量词)数据"""
    try:
        # 使用pandas读取Excel文件
        df = pd.read_excel(file_path)
        
        # 获取第一列名称(流量词)
        first_column_name = df.columns[0]
        
        # 提取第一列(流量词)的所有数据
        traffic_words = df[first_column_name].tolist()
        
        # 过滤掉NaN值
        traffic_words = [word for word in traffic_words if pd.notna(word)]
        
        # 如果需要保存到文件
        if save_to_file:
            with open(output_file, "w", encoding="utf-8") as f:
                for word in traffic_words:
                    if pd.notna(word):  # 检查是否为NaN值
                        f.write(f"{word}\n")
            print(f"流量词已保存到 '{output_file}' 文件")
        
        return traffic_words
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{file_path}'")
        raise
    except Exception as e:
        print(f"错误: {e}")
        raise

def get_img_analyze(my_image_path, amazon_image_path):
    """分析两张图片是否为竞品关系"""
    # 构建图片路径格式
    my_image_url = f"file://{os.path.abspath(my_image_path)}"
    amazon_image_url = f"file://{os.path.abspath(amazon_image_path)}"
    
    messages = [
        {
            "role": "system",
            "content": [{"text": SYSTEM_PROMPT}]
        },
        {
            "role": "user",
            "content": [
                {"image": my_image_url},
                {"image": amazon_image_url},
                {"text": USER_PROMPT}
            ]
        }
    ]
    
    response = MultiModalConversation.call(
        api_key=API_KEY,
        model=MODEL_NAME,
        messages=messages,
        vl_high_resolution_images=True
    )
    
    return get_img_conclusion(response["output"]["choices"][0]["message"]["content"][0]["text"].strip())

def get_img_conclusion(content):
    """从分析结果中提取结论"""
    try:
        lines = content.split('\n')
        for line in lines:
            if '结论：' in line or '结论:' in line:
                conclusion = line.split('：')[-1].strip() if '：' in line else line.split(':')[-1].strip()
                return conclusion
        # 如果找不到显式的结论行，尝试第一行
        return content.split('\n')[0].split('：')[-1].strip() if '：' in content.split('\n')[0] else content.split('\n')[0].split(':')[-1].strip()
    except:
        # 默认返回NO，以避免误判
        return 'NO'

def get_title_analyze(my_words, title):
    """分析标题中是否包含关键词"""
    if not my_words or not title:
        return 'NO'
    
    for word in my_words.split(' '):
        if word and word.strip() and word.strip().lower() not in title.lower():
            return 'NO'
    return 'YES'

def calculate_similarity_level(competitor_count, total_count):
    """计算相似度级别"""
    if total_count == 0:
        return "无法评估"
    
    percentage = (competitor_count / total_count) * 100
    
    if percentage >= 50:
        return "高度相似"
    elif percentage >= 30:
        return "中度相似"
    else:
        return "低度相似"

#####################################
# 浏览器设置和管理
#####################################

def configure_chrome_options(headless=False, proxy=None, user_agent=None):
    """配置Chrome浏览器选项"""
    chrome_options = Options()
    
    # 设置用户代理
    if user_agent is None:
        user_agent = get_random_user_agent()
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    # 如有请求，配置无头模式
    if headless:
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--window-size=1920,1080')
    
    # 如果提供了代理，则添加
    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')
    
    # 其他使浏览器更稳定的选项
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 防止自动化检测
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    return chrome_options

@contextmanager
def create_driver(headless=False, proxy=None, user_agent=None, window_size=(1366, 768)):
    """创建并管理Chrome WebDriver，确保适当的设置和清理"""
    driver = None
    try:
        # 配置并创建驱动程序
        options = configure_chrome_options(headless, proxy, user_agent)
        driver = webdriver.Chrome(options=options)
        
        # 设置窗口大小
        driver.set_window_size(*window_size)
        
        # 执行CDP命令以防止检测
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // 重写'plugins'属性以使用自定义getter
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // 重写'languages'属性以使用自定义getter
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'zh-CN'],
                });
            '''
        })
        
        yield driver
    finally:
        # 确保驱动程序最终被关闭
        if driver:
            driver.quit()

#####################################
# 元素交互辅助函数
#####################################

def safe_find_element(driver, locator_strategies, wait_time=10, parent_element=None):
    """使用多种定位策略安全地查找元素"""
    for by, selector in locator_strategies:
        try:
            if parent_element:
                # 如果有父元素，直接在其中搜索
                return parent_element.find_element(by, selector)
            else:
                # 否则使用wait在整个页面中查找元素
                element = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((by, selector))
                )
                return element
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            continue
    return None

def safe_find_elements(driver, locator_strategies, wait_time=10, parent_element=None):
    """使用多种定位策略安全地查找多个元素"""
    for by, selector in locator_strategies:
        try:
            if parent_element:
                # 如果有父元素，直接在其中搜索
                elements = parent_element.find_elements(by, selector)
                if elements:
                    return elements
            else:
                # 否则使用wait在整个页面中查找至少一个元素
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((by, selector))
                )
                elements = driver.find_elements(by, selector)
                if elements:
                    return elements
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            continue
    return []

def safe_click(driver, element, fallback_js=True, retries=3):
    """安全地点击元素，如果普通点击失败则回退到JavaScript点击"""
    for attempt in range(retries):
        try:
            element.click()
            return True
        except StaleElementReferenceException:
            if attempt < retries - 1:
                # 重试前稍等片刻
                time.sleep(0.5)
                continue
            else:
                return False
        except ElementNotInteractableException:
            if fallback_js and element:
                try:
                    driver.execute_script("arguments[0].click();", element)
                    return True
                except:
                    pass
            return False
    return False

def safe_send_keys(element, text, clear_first=True, click_first=True, retries=3):
    """安全地向元素发送按键"""
    for attempt in range(retries):
        try:
            if click_first:
                element.click()
            if clear_first:
                element.clear()
            element.send_keys(text)
            return True
        except StaleElementReferenceException:
            if attempt < retries - 1:
                # 重试前稍等片刻
                time.sleep(0.5)
                continue
            else:
                return False
        except:
            return False
    return False

def wait_for_page_load(driver, timeout=30):
    """等待页面完全加载"""
    try:
        # 等待DOM准备就绪
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        return True
    except:
        return False

#####################################
# 亚马逊爬虫函数
#####################################

def open_amazon(driver, url="https://www.amazon.com", wait_time=15):
    """打开亚马逊网站并验证是否正确加载"""
    try:
        print(f"正在打开亚马逊网站: {url}")
        driver.get(url)
        
        # 等待页面加载
        wait_for_page_load(driver)
        
        # 可能的亚马逊logo标识符
        logo_locators = [
            (By.ID, "nav-logo-sprites"),
            (By.CLASS_NAME, "nav-logo-base"),
            (By.CSS_SELECTOR, ".nav-sprite.nav-logo-base"),
            (By.XPATH, "//a[contains(@aria-label, 'Amazon')]"),
        ]
        
        # 等待亚马逊logo以确认页面已加载
        logo = safe_find_element(driver, logo_locators, wait_time)
        
        if logo:
            print("亚马逊网站加载成功")
            
            # 添加随机延迟使自动化行为不易被检测
            random_sleep(15, 20)
            return True
        else:
            print("亚马逊logo未找到，但页面已加载")
            # 检查我们是否在验证码或验证页面上
            if "captcha" in driver.page_source.lower() or "verification" in driver.page_source.lower():
                print("检测到验证码或验证页面")
            return False
            
    except Exception as e:
        print(f"打开亚马逊网站时出错: {e}")
        return False

def search_amazon(driver, search_term, wait_time=15):
    """在亚马逊上搜索产品"""
    
    # 定义多个搜索框定位策略
    search_box_locators = [
        (By.ID, "twotabsearchtextbox"),
        (By.NAME, "field-keywords"),
        (By.XPATH, "//input[@type='text' and contains(@id, 'search')]"),
        (By.CSS_SELECTOR, "input[type='text'][name='field-keywords']"),
    ]
    
    # 使用多种策略查找搜索框
    print(f"搜索 '{search_term}'")
    search_box = safe_find_element(driver, search_box_locators, wait_time)
    
    if search_box:
        print("找到搜索框，输入搜索词")
        # 在与搜索框交互前添加小延迟
        random_sleep(0.5, 1.5)
        
        if safe_send_keys(search_box, search_term):
            # 提交前再添加一个小延迟
            random_sleep(0.5, 1.5)
            
            # 尝试提交表单
            try:
                search_box.send_keys(Keys.RETURN)
                print("使用回车键提交搜索")
            except Exception as e:
                print(f"回车键提交失败: {e}")
                
                # 尝试查找并点击搜索按钮
                search_button_locators = [
                    (By.ID, "nav-search-submit-button"),
                    (By.CSS_SELECTOR, "input.nav-input[type='submit']"),
                    (By.XPATH, "//input[@type='submit' and contains(@class, 'nav-input')]"),
                ]
                
                search_button = safe_find_element(driver, search_button_locators, wait_time)
                if search_button and safe_click(driver, search_button):
                    print("通过点击搜索按钮提交搜索")
                else:
                    # 最后手段: 使用JavaScript提交表单
                    print("使用JavaScript提交搜索")
                    driver.execute_script(
                        "document.querySelector('form[name=\"site-search\"], form[role=\"search\"], form#nav-search-bar-form').submit();"
                    )
            
            # 等待页面加载
            wait_for_page_load(driver)
            
            # 等待搜索结果加载
            result_locators = [
                (By.CSS_SELECTOR, ".s-result-item"),
                (By.CSS_SELECTOR, "[data-component-type='s-search-result']"),
                (By.CSS_SELECTOR, ".sg-col-inner"),
            ]
            
            results = safe_find_elements(driver, result_locators, wait_time)
            
            if results:
                print(f"搜索结果加载成功 (找到 {len(results)} 项)")
                # 添加随机延迟使自动化行为不易被检测
                random_sleep(1, 3)
                return True
            else:
                print("未找到搜索结果")
                return False
        else:
            print("输入搜索词失败")
            return False
    else:
        # 如果找不到搜索框，尝试JavaScript注入
        print("未找到搜索框，尝试JavaScript注入")
        try:
            driver.execute_script(
                """
                // 尝试搜索框的多个可能的选择器
                var searchBox = document.querySelector('#twotabsearchtextbox, input[name=\"field-keywords\"]');
                if (searchBox) {
                    searchBox.value = arguments[0];
                    var form = searchBox.closest('form');
                    if (form) form.submit();
                }
                """, 
                search_term
            )
            print("通过JavaScript执行搜索")
            
            # 等待页面加载
            wait_for_page_load(driver)
            
            # 等待是否出现结果
            result_locators = [
                (By.CSS_SELECTOR, ".s-result-item"),
                (By.CSS_SELECTOR, "[data-component-type='s-search-result']"),
                (By.CSS_SELECTOR, ".sg-col-inner"),
            ]
            
            results = safe_find_elements(driver, result_locators, wait_time)
            
            if results:
                print(f"通过JavaScript成功加载搜索结果 (找到 {len(results)} 项)")
                # 添加随机延迟使自动化行为不易被检测
                random_sleep(1, 3)
                return True
            else:
                print("JavaScript注入后未找到搜索结果")
                return False
        except Exception as e:
            print(f"JavaScript搜索注入失败: {e}")
            return False

def download_image(image_url, folder_path, product_title, product_number):
    """下载图片并保存到指定文件夹，使用产品标题作为文件名"""
    product_title = product_title.lower()
    try:
        # 清理标题，将非下划线的符号替换为下划线
        import re
        clean_title = re.sub(r'[^\w\s]', '_', product_title)  # 将非字母数字下划线的字符替换为下划线
        clean_title = re.sub(r'\s+', '_', clean_title)  # 将空格替换为下划线
        
        # 如果标题过长，截取一部分以防文件名过长
        if len(clean_title) > 100:
            clean_title = clean_title[:100]
        
        # 创建图片文件名 - 使用产品标题
        image_filename = f"{clean_title}.jpg"
        
        # 如果出现任何错误，回退到编号命名
        if not clean_title:
            image_filename = f"产品{product_number}.jpg"
        
        image_path = os.path.join(folder_path, image_filename)
        
        # 确保文件夹存在
        os.makedirs(folder_path, exist_ok=True)
        
        # 下载图片
        response = requests.get(image_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"图片成功保存为 {image_filename}")
            return True
        else:
            print(f"下载图片失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"下载图片时出错: {e}")
        return False

def extract_products(driver, search_term, max_products=10):
    """从搜索结果中提取产品信息并下载图片"""
    
    print(f"提取'{search_term}'的最多 {max_products} 个产品信息")
    
    # 确保存放图片的目录存在
    base_dir = "images"
    search_dir = os.path.join(base_dir, search_term)
    os.makedirs(search_dir, exist_ok=True)
    
    # 产品容器定位器
    product_locators = [
        (By.CSS_SELECTOR, "[data-component-type='s-search-result']"),
        (By.CSS_SELECTOR, ".s-result-item"),
        (By.CSS_SELECTOR, ".sg-col-inner .a-section")
    ]
    
    # 查找产品容器
    product_elements = safe_find_elements(driver, product_locators)
    
    if not product_elements:
        print("未找到产品元素")
        return []
    
    products = []
    count = 0
    
    for product_element in product_elements:
        if count >= max_products:
            break
            
        try:
            # 提取产品数据
            product_data = {}
            
            # 标题
            title_locators = [
                (By.CSS_SELECTOR, "h2 a span"),
                (By.CSS_SELECTOR, ".a-size-medium.a-color-base.a-text-normal"),
                (By.CSS_SELECTOR, ".a-link-normal .a-text-normal")
            ]
            title_element = safe_find_element(driver, title_locators, parent_element=product_element)
            if title_element:
                product_data['title'] = title_element.text.strip()
            
            # 图片
            image_locators = [
                (By.CSS_SELECTOR, ".s-image"),
                (By.CSS_SELECTOR, "img[data-image-latency='s-product-image']"),
                (By.CSS_SELECTOR, ".a-section img"),
                (By.XPATH, ".//img[contains(@class, 's-image') or contains(@class, 'product-image')]")
            ]
            image_element = safe_find_element(driver, image_locators, parent_element=product_element)
            if image_element:
                # 尝试获取高质量图片URL
                src = image_element.get_attribute("src")
                srcset = image_element.get_attribute("srcset")
                
                # 如果有srcset，从中提取最高分辨率图片
                if srcset:
                    try:
                        # 解析srcset获取最高分辨率图片
                        srcset_parts = srcset.split(',')
                        high_res_src = srcset_parts[-1].strip().split(' ')[0]
                        if high_res_src:
                            src = high_res_src
                    except:
                        pass
                        
                product_data['image_url'] = src
                
                # 下载图片，现在使用标题作为文件名
                if src and 'title' in product_data:
                    if download_image(src, search_dir, product_data['title'], count + 1):
                        product_data['image_saved'] = True
                    else:
                        product_data['image_saved'] = False
            
            # 只有当我们至少有标题时才添加产品
            if 'title' in product_data:
                products.append(product_data)
                count += 1
                print(f"提取的产品 {count}: {product_data['title'][:50]}...")
                
        except Exception as e:
            print(f"提取产品数据时出错: {e}")
            continue
    
    print(f"成功提取 {len(products)} 个'{search_term}'的产品")
    return products

#####################################
# 整合工作流程
#####################################

def save_results_to_excel(similarity_results, output_file="产品相似度分析结果.xlsx"):
    """将结果保存到Excel"""
    # 转换为DataFrame
    results_list = []
    for product, details in similarity_results.items():
        row = {"产品名": product}
        row.update(details)
        
        # 如果竞品列表是一个列表，将其转换为字符串
        if "竞品列表" in row and isinstance(row["竞品列表"], list):
            row["竞品列表"] = ", ".join(row["竞品列表"])
            
        results_list.append(row)
    
    df = pd.DataFrame(results_list)
    
    # 保存到Excel
    df.to_excel(output_file, index=False)
    print(f"结果已保存到 {output_file}")

def integrated_workflow(excel_file='./红白蓝五星窗户灯词库_更新_20250318_151413.xlsx'):
    """整合的工作流程函数"""
    
    # 1. 从Excel中提取搜索词
    print("步骤1: 从Excel提取搜索词")
    search_terms = extract_my_product_name(excel_file)
    print(f"共提取 {len(search_terms)} 个搜索词")
    
    # 确保图片目录存在
    os.makedirs("images", exist_ok=True)
    os.makedirs(MY_IMAGE_DIRECTORY, exist_ok=True)
    
    # 结果字典
    similarity_results = {}
    
    # 2. 对每个搜索词进行处理
    for idx, search_term in enumerate(search_terms):
        print(f"\n处理进度: [{idx+1}/{len(search_terms)}]")
        print(f"开始处理搜索词: {search_term}")
        
        # 检查我的产品图片是否存在
        my_product_file = None
        for file in os.listdir(MY_IMAGE_DIRECTORY):
            if os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS:
                product_name = os.path.splitext(file)[0]
                if search_term == product_name:
                    my_product_file = os.path.join(MY_IMAGE_DIRECTORY, file)
                    break
        
        if not my_product_file:
            print(f"警告: 找不到与搜索词 '{search_term}' 匹配的产品图片")
            similarity_results[search_term] = {
                "相似度": "无法评估",
                "原因": "找不到匹配的产品图片",
                "竞品数量": 0,
                "总商品数": 0,
                "竞品百分比": 0,
                "竞品列表": []
            }
            continue
        
        # 爬取亚马逊产品
        amazon_dir = os.path.join("images", search_term)
        if not os.path.exists(amazon_dir) or len([f for f in os.listdir(amazon_dir) if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]) == 0:
            os.makedirs(amazon_dir, exist_ok=True)
            
            try:
                # 使用上下文管理器创建和使用Web驱动程序
                with create_driver(headless=False) as driver:
                    print("浏览器成功初始化")
                    
                    # 打开亚马逊
                    if open_amazon(driver):
                        # 搜索产品
                        if search_amazon(driver, search_term):
                            # 提取产品信息并下载图片
                            products = extract_products(driver, search_term, max_products=100)
                            
                            if not products:
                                print(f"未能提取到'{search_term}'的产品信息")
                                similarity_results[search_term] = {
                                    "相似度": "无法评估",
                                    "原因": "未找到相关产品",
                                    "竞品数量": 0,
                                    "总商品数": 0,
                                    "竞品百分比": 0,
                                    "竞品列表": []
                                }
                                continue
                        else:
                            print(f"搜索 '{search_term}' 失败")
                            similarity_results[search_term] = {
                                "相似度": "无法评估",
                                "原因": "搜索失败",
                                "竞品数量": 0,
                                "总商品数": 0,
                                "竞品百分比": 0,
                                "竞品列表": []
                            }
                            continue
                    else:
                        print("打开亚马逊网站失败")
                        similarity_results[search_term] = {
                            "相似度": "无法评估",
                            "原因": "打开亚马逊失败",
                            "竞品数量": 0,
                            "总商品数": 0,
                            "竞品百分比": 0,
                            "竞品列表": []
                        }
                        continue
            
            except WebDriverException as e:
                print(f"WebDriver错误: {e}")
                similarity_results[search_term] = {
                    "相似度": "无法评估",
                    "原因": f"WebDriver错误: {str(e)[:100]}",
                    "竞品数量": 0,
                    "总商品数": 0,
                    "竞品百分比": 0,
                    "竞品列表": []
                }
                continue
            except Exception as e:
                print(f"意外错误: {e}")
                similarity_results[search_term] = {
                    "相似度": "无法评估",
                    "原因": f"意外错误: {str(e)[:100]}",
                    "竞品数量": 0,
                    "总商品数": 0,
                    "竞品百分比": 0,
                    "竞品列表": []
                }
                continue
        else:
            print(f"使用已爬取的图片 ({len([f for f in os.listdir(amazon_dir) if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS])} 张)")
        
        # 获取我的产品关键词
        try:
            my_product_keywords = get_keyword(
                API_KEY, 
                BASE_URL, 
                'qwen-max-2025-01-25', 
                search_term
            )
            print(f"产品 '{search_term}' 的关键词: {my_product_keywords}")
        except Exception as e:
            print(f"获取关键词出错: {e}")
            my_product_keywords = search_term
        
        # 计算相似度
        total_count = 0
        competitor_count = 0
        competitors = []
        
        # 遍历亚马逊产品目录中的所有图片
        for file in os.listdir(amazon_dir):
            if os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS:
                total_count += 1
                amazon_product_file = os.path.join(amazon_dir, file)
                
                try:
                    print(f"分析产品 '{file}'...")
                    # 图像分析
                    img_conclusion = get_img_analyze(my_product_file, amazon_product_file)
                    print(f"图像分析结论: {img_conclusion}")
                    
                    # 标题分析
                    title_conclusion = get_title_analyze(my_product_keywords, file)
                    print(f"标题分析结论: {title_conclusion}")
                    
                    # 综合结论
                    conclusion = 'YES' if img_conclusion == 'YES' and title_conclusion == 'YES' else 'NO'
                    
                    if conclusion == 'YES':
                        competitor_count += 1
                        competitors.append(file)
                        print(f"产品 '{file}' 是竞品 ✅")
                    else:
                        print(f"产品 '{file}' 不是竞品 ❌")
                except Exception as e:
                    print(f"分析产品时出错 '{file}': {e}")
        
        # 计算相似度级别
        similarity_level = calculate_similarity_level(competitor_count, total_count)
        
        # 将结果添加到字典
        similarity_results[search_term] = {
            "相似度": similarity_level,
            "竞品数量": competitor_count,
            "总商品数": total_count,
            "竞品百分比": round((competitor_count / total_count * 100), 2) if total_count > 0 else 0,
            "竞品列表": competitors
        }
        
        # 每处理完一个搜索词就保存一次中间结果
        save_results_to_excel(similarity_results)
    
    # 3. 输出最终结果并保存到Excel
    print("\n步骤3: 输出最终结果并保存到Excel")
    save_results_to_excel(similarity_results)
    
    return similarity_results

#####################################
# 主程序
#####################################

if __name__ == "__main__":
    integrated_workflow()