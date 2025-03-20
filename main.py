import time
import random
import os
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
import requests
from contextlib import contextmanager
from get_my_product_name import extract_my_product_name

# 尝试导入fake_useragent，如果不可用则使用备用用户代理列表
try:
    from fake_useragent import UserAgent
    def get_random_user_agent():
        ua = UserAgent()
        return ua.random
except ImportError:
    # 备用用户代理列表
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36',
    ]
    def get_random_user_agent():
        return random.choice(USER_AGENTS)

# 添加随机延迟使自动化行为不易被检测
def random_sleep(min_seconds=1, max_seconds=3):
    """随机睡眠一段时间"""
    sleep_time = random.uniform(min_seconds, max_seconds)
    time.sleep(sleep_time)

# 浏览器设置和管理
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

# 元素交互辅助函数
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

# 亚马逊特定函数
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

# 主函数
def main():
    """主函数，协调亚马逊爬取过程"""
    print("启动亚马逊爬虫")
    
    # 搜索商品列表
    search_terms = extract_my_product_name('./红白蓝五星窗户灯词库_更新_20250318_151413.xlsx')
    
    # 确保主要图片目录存在
    base_dir = "images"
    os.makedirs(base_dir, exist_ok=True)
    
    try:
        # 使用上下文管理器创建和使用Web驱动程序
        with create_driver(headless=False) as driver:
            print("浏览器成功初始化")
            
            # 打开亚马逊
            if open_amazon(driver):
                
                # 遍历所有搜索词
                for search_term in search_terms:
                    print(f"\n开始处理搜索词: {search_term}")
                    
                    # 搜索产品
                    if search_amazon(driver, search_term):
                        # 提取产品信息并下载图片
                        products = extract_products(driver, search_term, max_products=10)
                        
                        if not products:
                            print(f"未能提取到'{search_term}'的产品信息")
                        
                        # 暂停以防止被检测
                        random_sleep(3, 5)
                    else:
                        print(f"搜索 '{search_term}' 失败")
                
                print("\n所有搜索词处理完毕")
            else:
                print("打开亚马逊网站失败")
    
    except WebDriverException as e:
        print(f"WebDriver错误: {e}")
    except Exception as e:
        print(f"意外错误: {e}")
    
    print("亚马逊爬虫完成")

if __name__ == "__main__":
    main()