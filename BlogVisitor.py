# -*- coding: utf-8 -*-

# @Author: yooongchun
# @File: BlogVisitor.py
# @Time: 2018/6/19
# @Contact: yooongchun@foxmail.com
# @blog: https://blog.csdn.net/zyc121561
# @Description: CSDN博客访问

import requests
from bs4 import BeautifulSoup
from UA import FakeUserAgent
from database import IPPool, InfoPool
import time
from datetime import datetime, timedelta, timezone
import random
import threading
import re
import types
from enum import Enum
from matplotlib import pyplot as plt
import logging
import config

config.CONFIG(to_file=True, level="ERROR", file_path="blogger.log")


class CSDNBlogVisitor():
    """
    1.访问CSDN博客所有文章
    2.统计博客访问信息
    """

    def __init__(self,
                 bolgger="zyc121561",
                 proxy_database_name="IP.db",
                 info_database_name="../INFO.db"):
        self.__bloger = bolgger
        self.__host = "blog.csdn.net"
        self.__proxy_database_name = proxy_database_name
        self.__info_database_name = info_database_name
        self.__RETRY_TIMES = 10
        self.__sleep_factor = 0.5
        self.__proxy_ip = self.__update_ip()
        ''' 休眠时间策略：
        # INSTANT：1秒以内
        # IMMEDIATE：1到5秒
        # TEMPORARY：5到10秒，
        # SHORT：10到60秒，
        # MIDDLE：1分钟到10分钟，
        # LONG：10分钟到一个小时，
        # NIGHT：1个小时到3个小时
        '''
        self.__TYPE = Enum("TYPE", ('INSTANT', 'IMMEDIATE', 'TEMPORARY', 'SHORT', 'MIDDLE', 'LONG', 'NIGHT'))
        '''访问策略
        # RANDOM：随机访问
        # MEAN：平均访问
        # GAUSSIAN：高斯分布访问（根据现有访问量）
        '''
        self.__VISIT_STRATEGY = Enum("VISITOR", ('RANDOM', 'MEAN', 'GAUSSIAN'))

    def __update_ip(self):
        '''从数据库中获取IP地址'''
        IPs = IPPool(self.__proxy_database_name).pull(re_try_times=self.__RETRY_TIMES)
        if IPs is not None and len(IPs) > 0:
            logging.info(u"CSDNBlogVisitor:从数据库中更新代理IP...")
            self.__proxy_ip = (ip for ip in IPs)
        else:
            logging.error(u"CSDNBlogVisitor:从数据库中更新代理IP出错！")
            self.__proxy_ip = None

    def __next_ip(self):
        '''从数据库中获取IP地址,使用生成器进行循环获取'''
        if isinstance(self.__proxy_ip, types.GeneratorType):
            try:
                ip = next(self.__proxy_ip)
                return ip
            except Exception:
                self.__update_ip()
            try:
                ip = next(self.__proxy_ip)
                return ip
            except Exception:
                return None
        else:
            self.__update_ip()
            try:
                ip = next(self.__proxy_ip)
                return ip
            except Exception:
                return None

    def __proxies(self):
        ip = self.__next_ip()
        if ip is not None:
            try:
                IP = str(ip[0]) + ":" + str(ip[1])
            except Exception:
                return None
            proxies = {"http": "http://" + IP}
            return proxies
        else:
            return None

    def __parse_html_for_article_info(self, html):
        '''获取文章基本信息'''
        INFO = []
        soup = BeautifulSoup(html, "lxml")
        try:
            children = soup.find_all(
                "div", {"class", "article-item-box csdn-tracking-statistics"})
        except Exception:
            logging.error(u"CSDNBlogVisitor:解析html出错!")
            return None
        try:
            for child in children:
                info = {}
                info['id'] = child.attrs['data-articleid']
                info['href'] = child.a.attrs['href']
                info['title'] = re.sub(r"\s+|\n+", "", child.a.get_text())
                info['date'] = child.find("span", {"class": "date"}).get_text()
                text = child.find_all("span", {"class": "read-num"})
                info['read_num'] = int(
                    re.findall(r'\d+', text[0].get_text())[0])
                info['commit_num'] = int(
                    re.findall(r"\d+", text[1].get_text())[0])
                INFO.append(info)
        except Exception:
            logging.error(u"CSDNBlogVisitor:寻找文章信息出错！")
            return None
        return INFO

    def __sleep_strategy(self, TYPE):
        '''休眠策略'''
        if TYPE == self.__TYPE.INSTANT:
            return 1 * random.random()
        elif TYPE == self.__TYPE.IMMEDIATE:
            return 1 + 4 * random.random()
        elif TYPE == self.__TYPE.TEMPORARY:
            return 5 + 5 * random.random()
        elif TYPE == self.__TYPE.SHORT:
            return 10 + 50 * random.random()
        elif TYPE == self.__TYPE.MIDDLE:
            return 60 + 540 * random.random()
        elif TYPE == self.__TYPE.LONG:
            return 600 + 3000 * random.random()
        elif TYPE == self.__TYPE.NIGHT:
            return 3600 + 7200 * random.random()
        else:
            return 0

    def __visit_strategy_container(self, info, strategy):
        '''访问策略:对不同文章根据其现有的访问量进行概率生成访问的url'''
        # 计算访问的概率：根据其现有访问量计算
        urls = [one['href'] for one in info]
        nums = [int(one['read_num']) for one in info]
        if strategy == self.__VISIT_STRATEGY.RANDOM:
            return [random.choice(urls) for i in range(len(urls))]
        elif strategy == self.__VISIT_STRATEGY.MEAN:
            return urls
        elif strategy == self.__VISIT_STRATEGY.GAUSSIAN:
            '''轮盘法挑选'''
            SUM = sum(nums)
            d = [(url, num) for url, num in zip(urls, nums)]
            d2 = sorted(d, key=lambda x: x[1])
            nums = [one[1] for one in d2]
            urls = [one[0] for one in d2]
            P = [num / SUM for num in nums]
            P2 = [sum(P[0:i + 1]) for i in range(len(P))]
            URLs = []
            for i in range(len(P)):
                rp = random.random()
                prep = P2[0]
                for index, p in enumerate(P2):
                    if rp > prep and rp <= p:
                        URLs.append(urls[index])
                    prep = p
            return URLs
        else:
            return None

    def __visit_strategy(self, info):
        '''生成访问策略
        # 不同访问策略选中的概率分别为：
        # MEAN ：0.3
        # RANDOM：0.3
        # GAUSSIAN：0.4
        '''
        p = random.random()
        if p > 0.7:
            STRATEGY = self.__VISIT_STRATEGY.MEAN
        elif p > 0.4:
            STRATEGY = self.__VISIT_STRATEGY.RANDOM
        else:
            STRATEGY = self.__VISIT_STRATEGY.GAUSSIAN
        return self.__visit_strategy_container(info, STRATEGY)

    def article_info(self):
        page_num = 0
        INFO = []
        sleep = self.__sleep_strategy(
            self.__TYPE.IMMEDIATE) * self.__sleep_factor
        while True:
            time.sleep(sleep)
            page_num += 1
            blog_page_link = "http://blog.csdn.net/{}/article/list/{}".format(
                self.__bloger, page_num)
            logging.info(u"CSDNBlogVisitor:访问URL:{}".format(blog_page_link))
            re_conn_times = 3
            headers = FakeUserAgent().random_headers()
            response = None
            for i in range(re_conn_times):
                try:
                    response = requests.get(
                        url=blog_page_link, headers=headers, timeout=5)
                    break
                except Exception:
                    continue
            if response is None:
                logging.info(u"CSDNBlogVisitor:访问url出错：%s" % blog_page_link)
                return None
            info = self.__parse_html_for_article_info(response.text)
            if info is None:
                return None
            if len(info) > 0:
                INFO += info
            else:
                break
        return INFO

    def visitor(self, url, proxies):
        """访问url"""
        logging.info(u"CSDNBlogVisitor:访问URL:{}".format(url))
        headers = FakeUserAgent().random_headers()
        if proxies is None:
            logging.error(u"CSDNBlogVisitor:没有代理IP，退出当前访问！")
            return
        re_conn_times = 3
        code = None
        for i in range(re_conn_times):
            try:
                code = requests.get(
                    url=url, headers=headers, proxies=proxies,
                    timeout=5).status_code
                if int(code) == 200:
                    break
            except Exception:
                continue
        if code is None:
            logging.info(u"CSDNBlogVisitor:访问url出错：%s" % url)
            return
        if int(code) == 200:
            logging.info(u"CSDNBlogVisitor:访问URL成功，IP:{}".format(
                proxies["http"].replace("http://", "")))
        else:
            logging.info(u"CSDNBlogVisitor:访问URL失败，IP:{}".format(
                proxies["http"].replace("http://", "")))

    def multiple_visitor(self, info):
        """多线程访问"""
        thread_pool = []
        urls = self.__visit_strategy(info)
        for i in range(len(urls)):
            logging.info(u"CSDNBlogVisitor:进度：{}/{} \t{:.2f}%".format(
                i + 1, len(urls), (i + 1) / len(urls) * 100))
            if i % 10 == 0:
                proxies = self.__proxies()
            thr = threading.Thread(
                target=self.visitor, args=(urls[i], proxies))
            thr.start()
            sleep = self.__sleep_strategy(
                self.__TYPE.SHORT) * self.__sleep_factor
            time.sleep(sleep)
            thread_pool.append(thr)
        for thr in thread_pool:
            thr.join()

    def run(self):
        p = threading.Thread(target=self.saver)
        p.start()
        cnt = 0
        while True:
            cnt += 1
            st = time.time()
            logging.info(u"CSDNBlogVisitor:开始第{}轮访问！".format(cnt))
            if cnt == 1:
                info = self.article_info()
            if info is None or len(info) < 1:
                logging.info(u"CSDNBlogVisitor:获取文章信息出错，跳过！")
                sleep = self.__sleep_strategy(
                    self.__TYPE.TEMPORARY) * self.__sleep_factor
                time.sleep(sleep)
                continue
            READNUM_A = sum([one['read_num'] for one in info])
            logging.info(u"CSDNBlogVisitor:当前统计文章数：{}\t文章总访问次数：{}".format(
                len(info), READNUM_A))
            self.multiple_visitor(info)
            info = self.article_info()
            if info is None or len(info) < 1:
                logging.info(u"CSDNBlogVisitor:获取统计信息出错!")
                sleep = self.__sleep_strategy(
                    self.__TYPE.IMMEDIATE) * self.__sleep_factor
                time.sleep(sleep)
                continue
            READNUM_B = sum([one['read_num'] for one in info])
            logging.info(
                u"CSDNBlogVisitor:完成第{}轮访问，耗时：{:.2f}秒\n当前统计文章数：{}\t文章总访问次数：{}\t本轮有效访问次数：{}".
                    format(cnt,
                           time.time() - st, len(info), READNUM_B,
                           int(READNUM_B - READNUM_A)))
            st = time.time()
            sleep = self.__sleep_strategy(
                self.__TYPE.MIDDLE) * self.__sleep_factor
            while time.time() - st < sleep:
                logging.info(u"CSDNBlogVisitor:随机休眠剩余时间：{:.2f} 秒".format(
                    sleep - time.time() + st))
                time.sleep(1)

    def __plotter(self, info):
        '''绘制文章访问频率图表'''
        logging.info(u"CSDNBlogVisitor:绘制访问信息统计图...")
        cnt = []
        IDs = []
        for one in info:
            if "read_num" in one.keys() and "id" in one.keys():
                cnt.append(one['read_num'])
                IDs.append(one['id'])
        plt.figure("CSDN Visitor Counter Viewer")
        plt.subplot(211)
        plt.bar(range(len(IDs)), cnt)
        plt.xticks(rotation=60)
        plt.xticks(range(len(IDs)), IDs)
        plt.xlabel("Article ID")
        plt.ylabel("Visitor Number")
        plt.title("Visitor Number--Article ID Figure")

        READNUM = InfoPool(self.__info_database_name).pull()
        if READNUM is None or len(READNUM) < 1:
            logging.info(u"CSDNBlogVisitor:没有保存信息...")
        else:
            time = [num[0] for num in READNUM]
            id_num = [num[2] for num in READNUM]
            num = [num[3] for num in READNUM]

            plt.subplot(223)
            plt.plot(id_num)
            plt.xticks(rotation=60)
            plt.xticks(range(len(time)), time)
            plt.xlabel("Time")
            plt.ylabel("Article Number")

            plt.subplot(224)
            plt.plot(num)
            plt.xticks(rotation=60)
            plt.xticks(range(len(time)), time)
            plt.xlabel("Time")
            plt.ylabel("Visitor Number")
        plt.show()

    def viewer(self, VIEW_WITH_IMG=False):
        '''博客访问量可视化'''
        info = self.article_info()
        if info is None:
            logging.info(u"CSDNBlogVisitor:获取文章信息出错！")
            return
        logging.info(u"CSDNBlogVisitor:统计时间：{}\t统计文章数：{}\t总计访问量：{}".format(
            datetime.now(), len(info), sum([one['read_num'] for one in info])))
        if VIEW_WITH_IMG:
            self.__plotter(info)

    def saver(self, time_step=1 * 60 * 60):
        '''保存统计数据到数据库'''
        while True:
            logging.info(u"CSDNBlogVisitor-save:保存统计信息...")
            re_try_times = 5
            for i in range(re_try_times):
                info = self.article_info()
                if info is not None:
                    break
                else:
                    info = None
                    sleep = self.__sleep_strategy(
                        self.__TYPE.SHORT) * self.__sleep_factor
                    time.sleep(sleep)
            if info is None:
                logging.error(u"CSDNBlogVisitor-save:获取信息出错！")
                logging.info(u"CSDNBlogVisitor-save:休眠中...")
                time.sleep(time_step)
                continue
            try:
                total_read = sum([one['read_num'] for one in info])
                article_num = len(info)
                # 将时间转换为北京时间
                utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
                bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
                INFO = [
                    str(bj_dt).split(".")[0],
                    time.time(), article_num, total_read
                ]
                InfoPool(self.__info_database_name).push([INFO])
            except Exception:
                logging.error(u"CSDNBlogVisitor-save:信息统计出错！")
            finally:
                logging.info(u"CSDNBlogVisitor-save:休眠中...")
                time.sleep(time_step)


if __name__ == "__main__":
    visitor = CSDNBlogVisitor(bolgger="zyc121561")
    visitor.run()
    # visitor.viewer(VIEW_WITH_IMG=True)
