import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent

def setup_driver():
    """设置并配置Chrome浏览器驱动"""
    # 创建Chrome选项
    chrome_options = Options()
    
    # 添加随机User-Agent
    ua = UserAgent()
    chrome_options.add_argument(f'user-agent={ua.random}')
    
    # 其他有用的选项
    # chrome_options.add_argument('--headless')  # 无头模式，取消注释以启用
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # 创建WebDriver实例
    driver = webdriver.Chrome(options=chrome_options)
    
    # 设置窗口大小
    driver.set_window_size(1366, 768)
    
    return driver

def open_amazon(driver, url="https://www.amazon.com"):
    """打开亚马逊网站"""
    try:
        print(f"正在打开亚马逊网站: {url}")
        driver.get(url)
        
        # 等待页面加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "nav-logo-sprites"))
        )
        
        print("亚马逊网站已成功加载")
        
        # 截图保存（可选）
        driver.save_screenshot("amazon_homepage.png")
        
        # 等待一段时间以便查看页面
        time.sleep(5)
        
        return True
    except Exception as e:
        print(f"打开亚马逊网站时出错: {e}")
        return False

def main():
    """主函数"""
    driver = None
    try:
        # 设置浏览器驱动
        driver = setup_driver()
        
        # 打开亚马逊网站
        success = open_amazon(driver)
        
        if success:
            print("成功打开亚马逊网站")
            # 在这里添加更多的爬虫逻辑
            
            # 搜索产品，使用更可靠的等待和多种定位策略
            try:
                # 首先尝试等待搜索框加载完成
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "nav-search-keywords"))
                )
                print("成功找到搜索框元素(通过ID)")
            except Exception as e:
                print(f"通过ID查找搜索框失败: {e}")
                try:
                    # 尝试使用XPath定位
                    search_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @id='nav-search-keywords']"))
                    )
                    print("成功找到搜索框元素(通过XPath)")
                except Exception as e:
                    print(f"通过XPath查找搜索框失败: {e}")
                    try:
                        # 尝试使用表单定位
                        form = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "nav-search-form"))
                        )
                        # 在表单中查找搜索框
                        search_box = form.find_element(By.TAG_NAME, "input")
                        print("成功找到搜索框元素(通过表单)")
                    except Exception as e:
                        print(f"通过表单查找搜索框失败: {e}")
                        print("无法找到搜索框，将尝试使用JavaScript注入")
                        # 使用JavaScript注入搜索词
                        driver.execute_script("document.querySelector('#nav-search-keywords, input[type=text]').value='laptop';")
                        driver.execute_script("document.getElementById('nav-search-form').submit();")
                        print("已使用JavaScript执行搜索")
                        search_box = None
            
            # 如果找到了搜索框元素，则正常输入和提交
            if search_box:
                search_box.clear()
                search_box.send_keys("laptop")
                try:
                    search_box.submit()
                except Exception as e:
                    print(f"提交搜索表单失败: {e}")
                    # 尝试点击搜索按钮
                    try:
                        search_button = driver.find_element(By.CSS_SELECTOR, ".nav-search-submit .nav-input")
                        search_button.click()
                        print("已点击搜索按钮")
                    except Exception as e:
                        print(f"点击搜索按钮失败: {e}")
                        # 尝试提交表单
                        try:
                            form = driver.find_element(By.ID, "nav-search-form")
                            form.submit()
                            print("已提交搜索表单")
                        except Exception as e:
                            print(f"提交搜索表单失败: {e}")
                            # 最后尝试使用JavaScript提交
                            driver.execute_script("document.getElementById('nav-search-form').submit();")
                            print("已使用JavaScript提交搜索")
            
            # 等待搜索结果加载
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".s-result-item"))
            )
            print("搜索结果已加载")
            
            # 保存搜索结果页面截图
            driver.save_screenshot("search_results.png")
            
        else:
            print("无法打开亚马逊网站")
            
    except Exception as e:
        print(f"程序执行过程中出错: {e}")
    finally:
        # 确保浏览器最终被关闭
        if driver:
            # 等待一段时间后关闭浏览器
            time.sleep(10)
            driver.quit()
            print("浏览器已关闭")

if __name__ == "__main__":
    main()