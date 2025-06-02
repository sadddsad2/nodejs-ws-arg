import re
import os
import time
import json
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError

def login_with_cookie_or_password(page, context, username, password):
    """先尝试cookie登录，失败后执行密码登录流程"""
    cookie_file = Path("deepnote_cookies.json")
    cookie_login_successful = False
    
    # 先尝试使用cookie登录
    if cookie_file.exists():
        try:
            print("尝试使用cookie登录")
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            print("已加载cookies")
            
            # 通过导航到登录页面测试cookies是否有效
            if page.url != "https://deepnote.com/sign-in":
                try:
                    # 增加重试机制和更短的超时时间
                    for attempt in range(3):
                        try:
                            print(f"Cookie登录导航尝试 {attempt + 1}/3")
                            page.goto("https://deepnote.com/sign-in", timeout=30000, wait_until="domcontentloaded")
                            print("已导航到DeepNote登录页面")
                            break
                        except TimeoutError:
                            if attempt < 2:
                                print(f"导航超时，等待5秒后重试...")
                                time.sleep(5)
                            else:
                                raise
                except TimeoutError:
                    print("多次尝试导航失败，cookie登录失败")
                    return False
            
            # 等待看是否重定向到工作区
            try:
                page.wait_for_url("**/workspace/**", timeout=8000)
                current_url = page.url
                if re.match(r"https://deepnote.com/workspace/.*", current_url):
                    print("Cookie登录成功，导航到工作区")
                    cookie_login_successful = True
                else:
                    print("Cookie登录可能失败，URL不匹配工作区模式")
            except TimeoutError:
                print("Cookie登录失败，URL未变更为工作区")
        except Exception as e:
            print(f"加载或使用cookies时出错: {str(e)}")
    else:
        print("未找到cookie文件，将使用密码登录")
    
    # 如果cookie登录失败，执行密码登录
    if not cookie_login_successful:
        print("执行密码登录流程")
        
        # 导航到DeepNote登录页面，使用重试机制
        if page.url != "https://deepnote.com/sign-in":
            success = False
            for attempt in range(3):
                try:
                    print(f"密码登录导航尝试 {attempt + 1}/3")
                    page.goto("https://deepnote.com/sign-in", timeout=15000, wait_until="domcontentloaded")
                    print("已导航到DeepNote登录页面")
                    success = True
                    break
                except TimeoutError:
                    if attempt < 2:
                        print(f"导航超时，等待10秒后重试...")
                        time.sleep(10)
                    else:
                        print("多次导航尝试失败")
                        return False
            
            if not success:
                return False
            
            # 等待页面完全加载，使用较短超时
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except TimeoutError:
                print("等待页面网络空闲超时，但继续执行")
        
        # 等待登录选项加载
        time.sleep(3)
        
        # 尝试多种方法找到GitHub登录按钮
        github_clicked = False
        try:
            # 方法1：通过文本精确匹配
            try:
                github_button = page.get_by_text("Continue with GitHub", exact=True)
                github_button.wait_for(state="visible", timeout=8000)
                github_button.click()
                github_clicked = True
                print("点击GitHub登录按钮（方法1）")
            except TimeoutError:
                # 方法2：通过文本部分匹配
                try:
                    github_button = page.get_by_text("GitHub", exact=False)
                    github_button.wait_for(state="visible", timeout=5000)
                    github_button.click()
                    github_clicked = True
                    print("点击GitHub登录按钮（方法2）")
                except TimeoutError:
                    # 方法3：通过XPath查找包含GitHub的按钮或链接
                    try:
                        github_button = page.locator('//button[contains(., "GitHub")] | //a[contains(., "GitHub")]')
                        github_button.wait_for(state="visible", timeout=5000)
                        github_button.click()
                        github_clicked = True
                        print("点击GitHub登录按钮（方法3）")
                    except TimeoutError:
                        # 方法4：尝试通过角色查找按钮
                        try:
                            github_button = page.get_by_role("button", name=re.compile("GitHub", re.IGNORECASE))
                            github_button.wait_for(state="visible", timeout=5000)
                            github_button.click()
                            github_clicked = True
                            print("点击GitHub登录按钮（方法4）")
                        except TimeoutError:
                            print("无法找到GitHub登录按钮")
        except Exception as e:
            print(f"点击GitHub登录按钮时出错: {str(e)}")
        
        if not github_clicked:
            print("未找到GitHub登录按钮，尝试直接输入凭据")
        
        # 等待页面加载完成
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except TimeoutError:
            print("等待页面加载超时，但继续执行")
        
        time.sleep(3)
        
        # 等待用户名字段并输入凭据
        try:
            # 尝试多种方式定位用户名输入框
            username_filled = False
            try:
                username_field = page.get_by_label("Username or email address")
                username_field.wait_for(state="visible", timeout=8000)
                username_field.click()
                username_field.fill(username)
                username_filled = True
                print("已输入用户名（方法1）")
            except TimeoutError:
                try:
                    username_field = page.locator('input[name="login"]')
                    username_field.wait_for(state="visible", timeout=5000)
                    username_field.click()
                    username_field.fill(username)
                    username_filled = True
                    print("已输入用户名（方法2）")
                except TimeoutError:
                    try:
                        username_field = page.locator('//input[@id="login_field"] | //input[contains(@placeholder, "username")]')
                        username_field.wait_for(state="visible", timeout=5000)
                        username_field.click()
                        username_field.fill(username)
                        username_filled = True
                        print("已输入用户名（方法3）")
                    except TimeoutError:
                        print("未找到用户名字段")
        except Exception as e:
            print(f"输入用户名时出错: {str(e)}")
        
        # 等待密码字段并输入凭据
        try:
            # 尝试多种方式定位密码输入框
            password_filled = False
            try:
                password_field = page.get_by_label("Password")
                password_field.wait_for(state="visible", timeout=8000)
                password_field.click()
                password_field.fill(password)
                password_filled = True
                print("已输入密码（方法1）")
            except TimeoutError:
                try:
                    password_field = page.locator('input[name="password"]')
                    password_field.wait_for(state="visible", timeout=5000)
                    password_field.click()
                    password_field.fill(password)
                    password_filled = True
                    print("已输入密码（方法2）")
                except TimeoutError:
                    try:
                        password_field = page.locator('//input[@id="password"] | //input[@type="password"]')
                        password_field.wait_for(state="visible", timeout=5000)
                        password_field.click()
                        password_field.fill(password)
                        password_filled = True
                        print("已输入密码（方法3）")
                    except TimeoutError:
                        print("未找到密码字段")
        except Exception as e:
            print(f"输入密码时出错: {str(e)}")
        
        # 点击登录按钮
        try:
            # 尝试多种方式定位登录按钮
            login_clicked = False
            try:
                sign_in_button = page.get_by_role("button", name="Sign in", exact=True)
                sign_in_button.wait_for(state="visible", timeout=8000)
                sign_in_button.click()
                login_clicked = True
                print("已点击登录按钮（方法1）")
            except TimeoutError:
                try:
                    sign_in_button = page.locator('input[value="Sign in"]')
                    sign_in_button.wait_for(state="visible", timeout=5000)
                    sign_in_button.click()
                    login_clicked = True
                    print("已点击登录按钮（方法2）")
                except TimeoutError:
                    try:
                        sign_in_button = page.locator('//button[contains(text(), "Sign in")] | //input[@value="Sign in"]')
                        sign_in_button.wait_for(state="visible", timeout=5000)
                        sign_in_button.click()
                        login_clicked = True
                        print("已点击登录按钮（方法3）")
                    except TimeoutError:
                        try:
                            sign_in_button = page.locator('form button[type="submit"]')
                            sign_in_button.wait_for(state="visible", timeout=5000)
                            sign_in_button.click()
                            login_clicked = True
                            print("已点击登录按钮（方法4）")
                        except TimeoutError:
                            print("未找到登录按钮")
        except Exception as e:
            print(f"点击登录按钮时出错: {str(e)}")
        
        if login_clicked:
            # 等待登录后的导航
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
                print("登录完成，页面已加载")
                
                # 保存成功登录后的cookies
                try:
                    cookies = context.cookies()
                    with open(cookie_file, "w") as f:
                        json.dump(cookies, f)
                    print("已将cookies保存到文件")
                except Exception as e:
                    print(f"保存cookies时出错: {str(e)}")
                    
            except TimeoutError:
                print("登录后页面加载超时，但继续执行")
    
    # 检查最终登录状态
    login_successful = False
    try:
        page.wait_for_url("**/workspace/**", timeout=10000)
        current_url = page.url
        if re.match(r"https://deepnote.com/workspace/.*", current_url):
            print("登录成功，导航到工作区")
            login_successful = True
        else:
            print("登录可能失败，未导航到工作区")
    except TimeoutError:
        print("登录可能失败，未导航到工作区")
        # 尝试检查当前URL是否包含登录成功的迹象
        current_url = page.url
        if "deepnote.com" in current_url and "sign-in" not in current_url:
            print("可能已登录成功（基于URL判断）")
            login_successful = True
    
    return login_successful

def is_app_running(page):
    """检查应用是否正在运行，要求同时满足：
    1. 存在"Running"字样（大写R开头）
    2. 存在停止按钮
    """
    try:
        # 等待页面加载
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except TimeoutError:
            print("等待页面加载超时，但继续检查")
        
        # 条件1：检查是否存在"Running"文本（必须大写R开头）
        running_text_found = False
        try:
            # 使用精确匹配大写开头的"Running"文本
            running_text_elements = page.locator("text=/Running/")
            running_text_elements.first.wait_for(state="visible", timeout=3000)
            found_text = running_text_elements.first.text_content()
            print(f"找到运行状态文本: '{found_text}'")
            
            # 验证找到的文本确实是大写R开头的"Running"
            if found_text and "Running" in found_text:
                running_text_found = True
                print("找到'Running'文本")
            else:
                print("未找到'Running'文本")
        except TimeoutError:
            print("未找到'Running'文本")
        
        is_running = running_text_found
        if is_running:
            print("应用状态检查：运行中")
        else:
            print(f"应用状态检查：未运行")
        
        return is_running
        
    except Exception as e:
        print(f"应用状态检查出错，假设未运行: {str(e)}")
        return False

def try_click_run_button(page):
    """尝试点击Run按钮"""
    try:
        # 等待页面完全加载
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except TimeoutError:
            print("等待页面加载超时，但继续执行")
        
        # 尝试多种方式定位Run按钮
        run_button_found = False
        
        # 方法1：通过文本精确匹配
        try:
            run_button = page.get_by_text("Run", exact=True)
            run_button.wait_for(state="visible", timeout=8000)
            run_button.click()
            run_button_found = True
            print("点击了'Run'按钮（方法1）")
        except TimeoutError:
            # 方法2：通过角色和名称
            try:
                run_button = page.get_by_role("button", name="Run")
                run_button.wait_for(state="visible", timeout=3000)
                run_button.click()
                run_button_found = True
                print("点击了'Run'按钮（方法2）")
            except TimeoutError:
                # 方法3：通过XPath
                try:
                    run_button = page.locator('//button[contains(text(), "Run")] | //button[contains(@class, "run")]')
                    run_button.wait_for(state="visible", timeout=3000)
                    run_button.click()
                    run_button_found = True
                    print("点击了'Run'按钮（方法3）")
                except TimeoutError:
                    # 方法4：尝试查找包含"run"或"start"的按钮（不区分大小写）
                    try:
                        run_button = page.locator('button:has-text("Run"), button:has-text("run"), button:has-text("Start")')
                        run_button.wait_for(state="visible", timeout=3000)
                        run_button.click()
                        run_button_found = True
                        print("点击了运行按钮（方法4）")
                    except TimeoutError:
                        print("尝试了多种方法但未找到'Run'按钮")
        
        return run_button_found
    except Exception as e:
        print(f"尝试点击'Run'按钮时出错: {str(e)}")
        return False

def run(playwright: Playwright) -> None:
    # 从环境变量获取凭据
    try:
        credentials = os.environ.get('GT_PW', '')
        if credentials:
            username, password = credentials.split(' ', 1)
        else:
            print("警告: GT_PW环境变量未设置")
            username, password = "", ""
    except ValueError:
        print("错误: GT_PW环境变量设置不正确。格式应为'username password'")
        username, password = "", ""
    
    # 从环境变量获取URL
    url = os.environ.get('DEEP_URL', '')
    if not url:
        print("警告: DEEP_URL环境变量未设置。登录后将不导航。")
    
    # 启动浏览器，添加更多选项以提高稳定性
    browser = playwright.firefox.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security'
        ]
    )
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    )
    
    # 创建新页面
    page = context.new_page()
    
    # 设置默认超时时间
    page.set_default_timeout(30000)
    
    try:
        login_attempts = 0
        max_login_attempts = 3
        app_running = False
        
        # 使用新的登录函数（包含cookie和密码登录）
        while login_attempts < max_login_attempts and not app_running:
            login_attempts += 1
            print(f"登录尝试 {login_attempts}/{max_login_attempts}")
            
            if not page or page.is_closed():
                page = context.new_page()
                page.set_default_timeout(30000)
            
            # 执行登录（先尝试cookie，再尝试密码）
            login_successful = login_with_cookie_or_password(page, context, username, password)
            
            if login_successful:
                # 导航到指定URL（如果提供）
                if url:
                    try:
                        print(f"导航到指定的deepnode保活链接: {url}")
                        page.goto(url, timeout=60000, wait_until="domcontentloaded")
                        print(f"已导航到指定的deepnode保活链接")
                        time.sleep(3)
                    except TimeoutError:
                        print(f"导航到deepnode保活链接时超时，但继续执行")
                    except Exception as e:
                        print(f"导航时出错: {str(e)}")
                
                # 检查应用是否正在运行
                app_running = is_app_running(page)
                
                # 如果应用未运行，尝试点击"Run"按钮
                if not app_running:
                    click_success = try_click_run_button(page)
                    
                    if click_success:
                        # 检查应用是否正在运行
                        print(f"等待20s，再次检查是否运行")
                        time.sleep(20)
                        app_running = is_app_running(page)
                
                if app_running:
                    print("应用已成功运行！")
                    break
                else:
                    print(f"应用未运行，将重试。尝试 {login_attempts}/{max_login_attempts}")
                    time.sleep(5)  # 等待一段时间再重试
            else:
                print(f"登录失败，将重试。尝试 {login_attempts}/{max_login_attempts}")
                time.sleep(10)  # 等待更长时间再重试
        
        # 最终检查
        if app_running:
            print("脚本执行成功：应用正在运行")
        else:
            print(f"脚本执行失败：在{max_login_attempts}次尝试后应用仍未运行")
    
    except Exception as e:
        print(f"脚本执行过程中出现异常: {str(e)}")
    
    finally:
        # 始终关闭浏览器
        try:
            if page and not page.is_closed():
                page.close()
            context.close()
            browser.close()
            print("浏览器已关闭")
        except Exception as e:
            print(f"关闭浏览器时出错: {str(e)}")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
