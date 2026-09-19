'''
Author: LetMeFly, Guo-Chenxu, Crsuh2er0, 420xincheng, tkzzzzzz6
Date: 2023-09-12 20:49:21
LastEditors: LetMeFly.xyz
LastEditTime: 2025-11-13 22:44:00
Description: 开源于https://github.com/LetMeFly666/YuketangAutoPlayer 欢迎issue、PR
'''
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (ElementClickInterceptedException,
                                          ElementNotInteractableException,
                                          StaleElementReferenceException)
from typing import List
from time import sleep
import time
import random
import os
import sys
import configparser

from question_answer import (
    OpenCodeQuestionSolver,
    QuestionAnswerError,
    answer_current_exercise,
)


def click_when_interactable(by=None, value=None, element=None, timeout=20):
    """等待并点击可交互元素；普通点击失败时使用 DOM 点击兜底。"""
    if element is None:
        def find_visible_enabled(current_driver):
            for candidate in current_driver.find_elements(by, value):
                try:
                    if candidate.is_displayed() and candidate.is_enabled():
                        return candidate
                except StaleElementReferenceException:
                    continue
            return False

        element = WebDriverWait(driver, timeout).until(find_visible_enabled)

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        element,
    )

    try:
        WebDriverWait(driver, timeout).until(
            lambda _: element.is_displayed() and element.is_enabled()
        )
        element.click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        # 某些雨课堂页面保留了可见但 Selenium 判定不可交互的标签节点。
        driver.execute_script("arguments[0].click();", element)

    return element


def create_config_template(config_path):
    """创建config.ini模板文件"""
    config = configparser.ConfigParser()
    config['Settings'] = {
        'headless': 'false',
        'course_url': 'https://在此填写你的课程URL',
        'cookie': '在此填写你的sessionid',
        'csrftoken': '在此填写你的csrftoken',
        'implicitly_wait': '10',
        'answer_questions': 'true',
        'auto_submit_answers': 'true',
        'answer_min_confidence': '0.00',
        'opencode_command': 'opencode',
        'opencode_model': '',
        'opencode_agent': 'compaction',
        'opencode_timeout': '120',
    }

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('; YuketangAutoPlayer 配置文件\n')
            f.write('; headless: 是否无窗口运行 (true/false)，首次使用建议false\n')
            f.write('; course_url: 你的课程地址，必须包含 https:// 协议头\n')
            f.write(';             例如: https://www.yuketang.cn/v2/web/studentLog/12345678\n')
            f.write('; cookie: 你的sessionid值，获取方式见README.md\n')
            f.write('; csrftoken: 同一雨课堂域名下的csrftoken，用于提交答案\n')
            f.write('; implicitly_wait: 元素查找超时时间(秒)，一般不需要修改\n\n')
            f.write('; answer_questions: 是否扫描并处理未完成习题\n')
            f.write('; auto_submit_answers: true自动提交，false只填写答案\n')
            f.write('; answer_min_confidence: 设为0表示只要模型给出答案就提交\n')
            f.write('; opencode_model: 留空使用OpenCode当前默认模型\n')
            f.write('; opencode_agent: 建议compaction（禁用工具，输入上下文较小）\n\n')
            config.write(f)
    except Exception as e:
        print(f'创建配置文件失败: {e}')


def load_config():
    """从config.ini加载配置"""
    config = configparser.ConfigParser()

    # 优先从可执行文件所在目录查找config.ini（支持打包后的exe）
    config_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'config.ini')

    if not os.path.exists(config_path):
        # 如果exe目录没有，尝试从当前工作目录查找
        config_path = os.path.join(os.getcwd(), 'config.ini')

    if not os.path.exists(config_path):
        # 如果config.ini不存在，创建模板
        print(f'未找到配置文件，正在创建模板: {config_path}')
        create_config_template(config_path)
        print('\n请编辑 config.ini 文件填写你的配置信息后重新运行程序')
        input('按回车键退出...')
        sys.exit(0)

    try:
        config.read(config_path, encoding='utf-8')
        print(f'成功加载配置文件: {config_path}')
        return config
    except Exception as e:
        print(f'读取配置文件失败: {e}')
        input('按回车键退出...')
        sys.exit(1)


# 加载配置
print('='*50)
print('YuketangAutoPlayer - 雨课堂视频自动播放器')
print('='*50)

config = load_config()

# 读取配置项
try:
    IF_HEADLESS = config.getboolean('Settings', 'headless', fallback=False)
    COURSE_URL = config.get('Settings', 'course_url', fallback='')
    COOKIE = config.get('Settings', 'cookie', fallback='')
    CSRF_TOKEN = config.get('Settings', 'csrftoken', fallback='')
    IMPLICITLY_WAIT = config.getint('Settings', 'implicitly_wait', fallback=10)
    ANSWER_QUESTIONS = config.getboolean('Settings', 'answer_questions', fallback=True)
    AUTO_SUBMIT_ANSWERS = config.getboolean(
        'Settings', 'auto_submit_answers', fallback=True
    )
    ANSWER_MIN_CONFIDENCE = config.getfloat(
        'Settings', 'answer_min_confidence', fallback=0.00
    )
    OPENCODE_COMMAND = config.get('Settings', 'opencode_command', fallback='opencode')
    OPENCODE_MODEL = config.get('Settings', 'opencode_model', fallback='')
    OPENCODE_AGENT = config.get('Settings', 'opencode_agent', fallback='compaction')
    OPENCODE_TIMEOUT = config.getint('Settings', 'opencode_timeout', fallback=120)
except Exception as e:
    print(f'\n配置文件格式错误: {e}')
    input('按回车键退出...')
    sys.exit(1)

# 验证配置
if not COURSE_URL or not COOKIE or '在此填写' in COURSE_URL or '在此填写' in COOKIE:
    print('\n错误: 检测到配置文件未正确填写!')
    print('请编辑 config.ini 文件，填写正确的 course_url 和 cookie')
    input('按回车键退出...')
    sys.exit(1)

print(f'\n配置信息:')
print(f'  无窗口模式: {IF_HEADLESS}')
print(f'  课程URL: {COURSE_URL[:50]}...' if len(COURSE_URL) > 50 else f'  课程URL: {COURSE_URL}')
print(f'  Cookie已配置: ✓')
print(f'  CSRF Token已配置: {bool(CSRF_TOKEN and "在此填写" not in CSRF_TOKEN)}')
print(f'  自动处理习题: {ANSWER_QUESTIONS}')
if ANSWER_QUESTIONS:
    print(f'  自动提交答案: {AUTO_SUBMIT_ANSWERS}')
    print(f'  答题方式: 本机 OpenCode ({OPENCODE_MODEL or "当前默认模型"})')
    print(f'  最低置信度: {ANSWER_MIN_CONFIDENCE:.2f}')
print('='*50 + '\n')


option = webdriver.ChromeOptions()

if IF_HEADLESS:
    option.add_argument('--headless')

driver = webdriver.Chrome(options=option)
driver.maximize_window()
driver.implicitly_wait(IMPLICITLY_WAIT)
IS_COMMONUI = False

def str2dic(s):
    d = dict()
    for i in s.split('; '):
        temp = i.split('=')
        d[temp[0]] = temp[1]
    return d


def setCookie(cookies):
    driver.delete_all_cookies()
    for name, value in cookies.items():
        driver.add_cookie({'name': name, 'value': value, 'path': '/'})


def ifVideo(div: WebElement):
    for i in div.find_elements(By.TAG_NAME, 'i'):
        i_class = i.get_attribute('class')
        if 'icon--suo' in i_class:  # 锁的图标，表明视频未开放
            return False

        # 新版 www.yuketang.cn 将课程内容放进 iframe，但条目仍使用该图标。
        if 'icon--shipin' in i_class:
            return True

    if IS_COMMONUI:  # www.yuketang.cn，非grsbupt.yuketang.cn，属新版ui
        try:
            span = div.find_element(By.CSS_SELECTOR, 'span.leaf-flag')
        except:
            return False
        return '视频' in span.text.strip()
    
    try:
        i = div.find_element(By.TAG_NAME, 'i')
    except:
        return False  # 每个小结后面都存在空行<li>
    i_class = i.get_attribute('class')
    return 'icon--shipin' in i_class


def ifExercise(div: WebElement):
    """识别普通作业/练习节点；正式考试不在自动处理范围内。"""
    text = div.text.strip()
    if '考试' in text or '试卷' in text:
        return False

    for icon in div.find_elements(By.TAG_NAME, 'i'):
        icon_class = (icon.get_attribute('class') or '').lower()
        if 'icon--suo' in icon_class:
            return False
        if any(word in icon_class for word in ('zuoye', 'lianxi', 'ceping', 'xiti', 'exercise')):
            return True

    try:
        flags = div.find_elements(By.CSS_SELECTOR, 'span.leaf-flag')
        if flags and any(
            word in flags[0].text for word in ('作业', '练习', '测评', '测试', '习题')
        ):
            return True
    except Exception:
        pass
    return bool(any(word in text for word in ('作业', '练习', '测评', '习题')))


def getAllvideos_notFinished(allClasses: List[WebElement]):
    driver.implicitly_wait(0.1)  # 找不到元素时会找满implicitly_wait秒
    allVideos = []
    for thisClass in allClasses:
        if ifVideo(thisClass) and '已完成' not in thisClass.text and '截止' not in thisClass.text:
            print(f'找到未完成的视频: {thisClass.text.strip()}')
            allVideos.append(thisClass)
    driver.implicitly_wait(IMPLICITLY_WAIT)
    return allVideos


def get1video_notFinished(allClasses: List[WebElement]):
    for thisClass in allClasses:
        if ifVideo(thisClass) and '已完成' not in thisClass.text and '截止' not in thisClass.text:
            return thisClass
    return None


def getAllExercises_notFinished(allClasses: List[WebElement]):
    driver.implicitly_wait(0.1)
    exercises = []
    try:
        for item in allClasses:
            text = item.text.strip()
            completed = any(word in text for word in ('已完成', '已提交', '已作答'))
            expired = '已过期' in text or '已截止' in text
            if ifExercise(item) and not completed and not expired:
                print(f'找到未完成的习题: {text}')
                exercises.append(item)
    finally:
        driver.implicitly_wait(IMPLICITLY_WAIT)
    return exercises


homePageURL = 'https://' + COURSE_URL.split('https://')[1].split('/')[0] + '/'
if 'www.yuketang.cn' in homePageURL:
    IS_COMMONUI = True
# driver.get('https://grsbupt.yuketang.cn/')
driver.get(homePageURL)
login_cookies = {'sessionid': COOKIE}
if CSRF_TOKEN and '在此填写' not in CSRF_TOKEN:
    login_cookies['csrftoken'] = CSRF_TOKEN
setCookie(login_cookies)
driver.get(COURSE_URL)
sleep(3)
if 'pro/portal/home' in driver.current_url:
    print('cookie失效或设置有误，请重设cookie或选择每次扫码登录')
    driver.get(homePageURL)
    driver.find_element(By.CLASS_NAME, 'login-btn').click()
    print("请扫码登录")
    while 'courselist' not in driver.current_url:  # 判断是否已经登录成功
        sleep(0.5)
    print('登录成功')
    driver.get(COURSE_URL)


def change2speed2():
    speedbutton = driver.find_element(By.TAG_NAME, 'xt-speedbutton')
    ActionChains(driver).move_to_element(speedbutton).perform()
    ul = speedbutton.find_element(By.TAG_NAME, 'ul')
    lis = ul.find_elements(By.TAG_NAME, 'li')
    li_speed2 = lis[0]
    diffY = speedbutton.location['y'] - li_speed2.location['y']
    # ActionChains(driver).move_to_element_with_offset(speedbutton, 3, 5).perform()
    # ActionChains(driver).click().perform()
    # 我也不知道为啥要一点一点移动上去，反正直接移动上去的话，点击是无效的
    for i in range(diffY // 10):  # 可能不是一个好算法
        ActionChains(driver).move_by_offset(0, -10).perform()
        sleep(0.5)
    sleep(0.8)
    ActionChains(driver).click().perform()


def mute1video():
    if driver.execute_script('return video.muted;'):
        return
    voice = driver.find_element(By.TAG_NAME, 'xt-volumebutton')
    ActionChains(driver).move_to_element(voice).perform()
    ActionChains(driver).click().perform()


def switch_to_video_context(timeout=30):
    """在当前页面及嵌套 iframe 中查找播放器。

    找到后会把 Selenium 保持在 video 所在的页面层级，方便后续脚本直接操作。
    """
    deadline = time.time() + timeout
    driver.implicitly_wait(0)

    def search_current_context():
        if driver.find_elements(By.TAG_NAME, 'video'):
            return True

        frames = driver.find_elements(By.TAG_NAME, 'iframe')
        for frame in frames:
            try:
                driver.switch_to.frame(frame)
                if search_current_context():
                    return True
                driver.switch_to.parent_frame()
            except Exception:
                # 页面加载时 iframe 可能被重新创建，返回顶层后下一轮重试。
                driver.switch_to.default_content()
                return False

        return False

    try:
        while time.time() < deadline:
            driver.switch_to.default_content()
            if search_current_context():
                return True
            sleep(1)
        driver.switch_to.default_content()
        return False
    finally:
        driver.implicitly_wait(IMPLICITLY_WAIT)


def finish1video():
    if IS_COMMONUI:
        iframe = WebDriverWait(driver, 20).until(
            lambda current_driver: current_driver.find_element(
                By.CSS_SELECTOR, 'iframe.tab-pane-content-iframe'
            )
        )
        driver.switch_to.frame(iframe)
        allClasses = WebDriverWait(driver, 20).until(
            lambda current_driver: current_driver.find_elements(By.CLASS_NAME, 'leaf-detail')
        )
    else:
        allClasses = driver.find_elements(By.CLASS_NAME, 'leaf-detail')
    print('正在寻找未完成的视频，请耐心等待')
    allVideos = getAllvideos_notFinished(allClasses)
    if not allVideos:
        return False
    video = allVideos[0]
    driver.execute_script('arguments[0].scrollIntoView(false);', video)
    original_window = driver.current_window_handle
    windows_before_click = set(driver.window_handles)
    click_when_interactable(element=video)
    print('正在播放')
    # 有的课程在新标签页打开，有的直接在当前页面或 iframe 内打开。
    try:
        WebDriverWait(driver, 5).until(
            lambda current_driver: len(current_driver.window_handles) > len(windows_before_click)
        )
    except Exception:
        pass

    new_windows = [
        handle for handle in driver.window_handles
        if handle not in windows_before_click
    ]
    video_window = new_windows[-1] if new_windows else driver.current_window_handle
    driver.switch_to.window(video_window)

    if not switch_to_video_context(timeout=30):
        screenshot_path = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])),
            'video_not_found.png',
        )
        driver.save_screenshot(screenshot_path)
        raise RuntimeError(
            f'未找到视频播放器，当前地址：{driver.current_url}；'
            f'页面截图已保存到：{screenshot_path}'
        )

    driver.execute_script('window.video = document.querySelector("video");')
    driver.execute_script('videoPlay = setInterval(function() {if (video.paused) {video.play();}}, 200);')
    driver.execute_script('setTimeout(() => clearInterval(videoPlay), 5000)')
    driver.execute_script('addFinishMark = function() {finished = document.createElement("span"); finished.setAttribute("id", "LetMeFly_Finished"); document.body.appendChild(finished); console.log("Finished");}')
    driver.execute_script('lastDuration = 0; setInterval(() => {nowDuration = video.currentTime; if (nowDuration < lastDuration) {addFinishMark()}; lastDuration = nowDuration}, 200)')
    driver.execute_script('video.addEventListener("pause", () => {video.play()})')
    mute1video()
    change2speed2()
    while True:
        if driver.execute_script('return document.querySelector("#LetMeFly_Finished");'):
            print('finished, wait 5s')
            sleep(5)  # 再让它播5秒
            if video_window != original_window:
                driver.close()
                driver.switch_to.window(original_window)
            else:
                # 当前标签页播放时不能关闭唯一窗口，重新进入课程目录即可。
                driver.switch_to.default_content()
                driver.get(COURSE_URL)
            return True
        else:
            print(f'正在播放视频 | not finished yet | 随机数: {random.random()}')
            sleep(3)
    return False


question_solver = OpenCodeQuestionSolver(
    command=OPENCODE_COMMAND,
    model=OPENCODE_MODEL,
    agent=OPENCODE_AGENT,
    timeout=OPENCODE_TIMEOUT,
    workdir=os.path.dirname(os.path.abspath(sys.argv[0])),
)
attempted_exercises = set()

if ANSWER_QUESTIONS and AUTO_SUBMIT_ANSWERS and not (
    CSRF_TOKEN and '在此填写' not in CSRF_TOKEN
):
    print(
        '警告：未配置csrftoken。题目可以选择，但提交时可能显示网络错误；'
        '请从同一雨课堂域名的浏览器Cookie中复制csrftoken到config.ini。'
    )


def finish1exercise():
    """寻找并处理一份本次运行尚未尝试的普通习题。"""
    driver.switch_to.default_content()
    if IS_COMMONUI:
        iframe = WebDriverWait(driver, 20).until(
            lambda current_driver: current_driver.find_element(
                By.CSS_SELECTOR, 'iframe.tab-pane-content-iframe'
            )
        )
        driver.switch_to.frame(iframe)
        allClasses = WebDriverWait(driver, 20).until(
            lambda current_driver: current_driver.find_elements(By.CLASS_NAME, 'leaf-detail')
        )
    else:
        allClasses = driver.find_elements(By.CLASS_NAME, 'leaf-detail')

    print('正在寻找未完成的习题，请耐心等待')
    exercises = getAllExercises_notFinished(allClasses)
    exercises = [
        item for item in exercises
        if item.text.strip() not in attempted_exercises
    ]
    if not exercises:
        return False

    if not question_solver.configured:
        print(
            '发现未完成习题，但没有找到OpenCode命令。请确认opencode已经安装、'
            '完成模型配置并加入PATH。'
        )
        return False

    exercise = exercises[0]
    exercise_name = exercise.text.strip()
    attempted_exercises.add(exercise_name)
    original_window = driver.current_window_handle
    windows_before_click = set(driver.window_handles)
    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', exercise)
    click_when_interactable(element=exercise)
    print(f'开始处理习题: {exercise_name}')

    try:
        WebDriverWait(driver, 6).until(
            lambda current_driver: len(current_driver.window_handles) > len(windows_before_click)
        )
    except Exception:
        pass

    new_windows = [
        handle for handle in driver.window_handles
        if handle not in windows_before_click
    ]
    exercise_window = new_windows[-1] if new_windows else driver.current_window_handle
    driver.switch_to.window(exercise_window)

    try:
        stats = answer_current_exercise(
            driver,
            question_solver,
            auto_submit=AUTO_SUBMIT_ANSWERS,
            min_confidence=ANSWER_MIN_CONFIDENCE,
            failure_dir=os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                'question_failures',
            ),
        )
        print(
            '习题处理结束 | '
            f'已填写/提交 {stats["answered"]} | '
            f'跳过 {stats["skipped"]} | 失败 {stats["failed"]}'
        )
    except QuestionAnswerError as exc:
        print(f'习题页面无法处理：{exc}')
    except Exception as exc:
        print(f'习题处理发生异常：{exc}')
    finally:
        try:
            if exercise_window != original_window and exercise_window in driver.window_handles:
                driver.close()
                driver.switch_to.window(original_window)
            else:
                driver.switch_to.default_content()
        finally:
            driver.get(COURSE_URL)
            sleep(5)

    return True


while finish1video():
    driver.refresh()
    sleep(5)  # thanks for @420xincheng's #8

if ANSWER_QUESTIONS:
    driver.switch_to.default_content()
    driver.get(COURSE_URL)
    sleep(5)
    while finish1exercise():
        sleep(3)

driver.quit()
print('处理结束：未完成视频和可识别的普通习题均已扫描')
sleep(5)
