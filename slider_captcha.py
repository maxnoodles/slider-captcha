import random
import time
import traceback
from contextlib import contextmanager

import cv2
import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


@contextmanager
def selenium(driver):
    try:
        yield
    except Exception as e:
        traceback.print_exc()
        driver.quit()


class SliderCaptcha():

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.driver = webdriver.Chrome(chrome_options=options)

        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        with selenium(self.driver):
            login_url = 'http://dun.163.com/trial/jigsaw'
            self.driver.maximize_window()
            self.driver.get(url=login_url)
            # 点击按钮，触发滑块
            self.driver.find_element_by_xpath(
                '//div[@class="yidun_slider"]'
            ).click()

            # 获取背景图并保存
            background = self.wait.until(
                lambda x: x.find_element_by_xpath('//img[@class="yidun_bg-img"]')
            ).get_attribute('src')
            with open('background.png', 'wb') as f:
                resp = requests.get(background)
                f.write(resp.content)

            # 获取滑块图并保存
            slider = self.wait.until(
                lambda x: x.find_element_by_xpath('//img[@class="yidun_jigsaw"]')
            ).get_attribute('src')
            with open('slider.png', 'wb') as f:
                resp = requests.get(slider)
                f.write(resp.content)

            distance = self.findfic(target='background.png', template='slider.png')
            print(distance)
            # 初始滑块距离边缘 4 px
            trajectory = self.get_tracks(distance + 4)
            print(trajectory)

            # 等待按钮可以点击
            slider_element = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, 'yidun_jigsaw'))
            )

            # 添加行动链
            ActionChains(self.driver).click_and_hold(slider_element).perform()
            for track in trajectory['plus']:
                ActionChains(self.driver).move_by_offset(
                    xoffset=track,
                    yoffset=round(random.uniform(1.0, 3.0), 1)
                ).perform()
            time.sleep(0.5)

            for back_tracks in trajectory['reduce']:
                ActionChains(self.driver).move_by_offset(
                    xoffset=back_tracks,
                    yoffset=round(random.uniform(1.0, 3.0), 1)
                ).perform()
            #
            for i in [-4, 4]:
                ActionChains(self.driver).move_by_offset(
                    xoffset=i,
                    yoffset=0
                ).perform()

            time.sleep(0.1)
            ActionChains(self.driver).release().perform()
            time.sleep(2)

    def close(self):
        self.driver.quit()

    def findfic(self, target='background.png', template='slider.png'):
        """

        :param target: 滑块背景图
        :param template: 滑块图片路径
        :return: 模板匹配距离
        """
        target_rgb = cv2.imread(target)
        target_gray = cv2.cvtColor(target_rgb, cv2.COLOR_BGR2GRAY)
        template_rgb = cv2.imread(template, 0)
        # 使用相关性系数匹配， 结果越接近1 表示越匹配
        # https://www.cnblogs.com/ssyfj/p/9271883.html
        res = cv2.matchTemplate(target_gray, template_rgb, cv2.TM_CCOEFF_NORMED)
        # opencv 的函数 minMaxLoc：在给定的矩阵中寻找最大和最小值，并给出它们的位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        # 因为滑块只需要 x 坐标的距离，放回坐标元组的 [0] 即可
        if abs(1 - min_val) <= abs(1 - max_val):
            distance = min_loc[0]
        else:
            distance = max_loc[0]
        return distance

    def get_tracks(self, distance):
        """

        :param distance: 缺口距离
        :return: 轨迹
        """
        # 分割加减速路径的阀值
        value = round(random.uniform(0.55, 0.75), 2)
        # 划过缺口 20 px
        distance += 20
        # 初始速度，初始计算周期， 累计滑动总距
        v, t, sum = 0, 0.3, 0
        # 轨迹记录
        plus = []
        # 将滑动记录分段，一段加速度，一段减速度
        mid = distance * value
        while sum < distance:
            if sum < mid:
                # 指定范围随机产生一个加速度
                a = round(random.uniform(2.5, 3.5), 1)
            else:
                # 指定范围随机产生一个减速的加速度
                a = -round(random.uniform(2.0, 3.0), 1)
            s = v * t + 0.5 * a * (t ** 2)
            v = v + a * t
            sum += s
            plus.append(round(s))

        # end_s = sum - distance
        # plus.append(round(-end_s))

        # 手动制造回滑的轨迹累积20px
        # reduce = [-3, -3, -2, -2, -2, -2, -2, -1, -1, -1]
        reduce = [-6, -4, -6, -4]
        return {'plus': plus, 'reduce': reduce}


def run():
    spider = SliderCaptcha()
    spider.login()
    spider.close()


if __name__ == '__main__':
    run()
