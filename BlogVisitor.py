# -*- coding: utf-8 -*-

# @Author: yooongchun
# @File: visit.py
# @Time: 2018/6/19
# @Contact: yooongchun@foxmail.com
# @blog: https://blog.csdn.net/zyc121561
# @Description: CSDN博客访问

import requests
from bs4 import BeautifulSoup
from UA import FakeUserAgent
from database import IP_Pool, INFO_Pool
import time
from datetime import datetime
import random
import threading
from multiprocessing import Process
import re
from matplotlib import pyplot as plt
import logging
import config
config.config()


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
        self.__table_name = "ip_table"
        self.__info_table_name = "info_table"
        self.__proxy_database_name = proxy_database_name
        self.__info_database_name = info_database_name
        self.__RETRY_TIMES = 10

    def __random_ip(self):
        ip = IP_Pool(self.__proxy_database_name, self.__table_name).pull(
            random_flag=True, re_try_times=self.__RETRY_TIMES)
        if ip is not None:
            return str(ip[0]) + ":" + str(ip[1])
        else:
            return None

    def __proxies(self):
        ip = self.__random_ip()
        if ip is not None:
            proxies = {"http": "http://" + ip}
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

    def article_info(self):
        page_num = 0
        INFO = []
        while True:
            time.sleep(5 * random.random())
            page_num += 1
            blog_page_link = "http://blog.csdn.net/{}/article/list/{}".format(
                self.__bloger, page_num)
            logging.info(u"CSDNBlogVisitor:访问URL:{}".format(blog_page_link))
            re_conn_times = 5
            headers = FakeUserAgent().random_headers()
            for i in range(re_conn_times):
                try:
                    response = requests.get(
                        url=blog_page_link, headers=headers, timeout=5)
                    break
                except Exception:
                    response = None
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

    def visit(self, url, proxies):
        """访问url"""
        logging.info(u"CSDNBlogVisitor:访问URL:{}".format(url))
        headers = FakeUserAgent().random_headers()
        if proxies is None:
            logging.error(u"CSDNBlogVisitor:没有代理IP，退出当前访问！")
            return
        re_conn_times = 3
        for i in range(re_conn_times):
            try:
                code = requests.get(
                    url=url, headers=headers, proxies=proxies,
                    timeout=5).status_code
                if int(code) == 200:
                    break
            except Exception:
                code = None
        if code is None:
            logging.info(u"CSDNBlogVisitor:访问url出错：%s" % url)
            return
        if int(code) == 200:
            logging.info(u"CSDNBlogVisitor:访问URL成功，IP:{}".format(
                proxies["http"].replace("http://", "")))
        else:
            logging.info(u"CSDNBlogVisitor:访问URL失败，IP:{}".format(
                proxies["http"].replace("http://", "")))

    def multiple_thread_visit(self, info):
        """多线程访问"""
        thread_pool = []
        urls = [one['href'] for one in info]
        proxies = self.__proxies()
        for i in range(len(urls)):
            logging.info(u"CSDNBlogVisitor:进度：{}/{}\t{:.2f}%".format(
                i + 1, len(urls), (i + 1) / len(urls) * 100))
            if i % 10 == 0:
                proxies = self.__proxies()
            thr = threading.Thread(target=self.visit, args=(urls[i], proxies))
            thr.start()
            time.sleep(random.random() * 5)
            thread_pool.append(thr)
        for thr in thread_pool:
            thr.join()

    def run(self):
        p = Process(target=self.save)
        p.start()
        cnt = 0
        while True:
            cnt += 1
            st = time.time()
            logging.info(u"CSDNBlogVisitor:开始第{}轮访问！".format(cnt))
            info = self.article_info()
            if info is None or len(info) < 1:
                logging.info(u"CSDNBlogVisitor:获取文章信息出错，跳过！")
                time.sleep(5 * random.random())
                continue
            READNUM_A = sum([one['read_num'] for one in info])
            logging.info(u"CSDNBlogVisitor:当前统计文章数：{}\t文章总访问次数：{}".format(
                len(info), READNUM_A))
            self.multiple_thread_visit(info)
            info = self.article_info()
            if info is None or len(info) < 1:
                logging.info(u"CSDNBlogVisitor:获取统计信息出错!")
                time.sleep(5 * random.random())
                continue
            READNUM_B = sum([one['read_num'] for one in info])
            logging.info(
                u"CSDNBlogVisitor:完成第{}轮访问，耗时：{:.2f}秒\n当前统计文章数：{}\t文章总访问次数：{}\t本轮有效访问次数：{}".
                format(cnt,
                       time.time() - st, len(info), READNUM_B,
                       int(READNUM_B - READNUM_A)))
            st = time.time()
            sleep = 60 * random.random()
            while time.time() - st < sleep:
                logging.info(u"CSDNBlogVisitor:随机休眠剩余时间：{:.2f} 秒".format(
                    sleep - time.time() + st))
                time.sleep(1)
        p.join()

    def __plot(self, info):
        '''绘制图表'''
        logging.info(u"CSDNBlogVisitor:绘制访问信息统计图...")
        cnt = []
        IDs = []
        for one in info:
            if "read_num" in one.keys() and "id" in one.keys():
                cnt.append(one['read_num'])
                IDs.append(one['id'])
        plt.figure("CSDN Visitor Counter Viewer")
        plt.bar(range(len(IDs)), cnt)
        plt.xticks(rotation=60, fontsize=10)
        plt.xticks(range(len(IDs)), IDs)
        plt.xlabel("Article ID")
        plt.ylabel("Visitor Number")
        plt.title("Visitor numver--Article ID figure")
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
            self.__plot(info)

    def save(self, time_step=1 * 60 * 60):
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
                    time.sleep(10)
            if info is None:
                logging.error(u"CSDNBlogVisitor-save:获取信息出错！")
                logging.info(u"CSDNBlogVisitor-save:休眠中...")
                time.sleep(time_step)
                continue
            try:
                total_read = sum([one['read_num'] for one in info])
                article_num = len(info)
                INFO = [
                    str(datetime.now()).split(".")[0],
                    time.time(), article_num, total_read
                ]
                INFO_Pool(self.__info_database_name,
                          self.__info_table_name).push([INFO])
            except Exception:
                logging.error(u"CSDNBlogVisitor-save:信息统计出错！")
            finally:
                logging.info(u"CSDNBlogVisitor-save:休眠中...")
                time.sleep(time_step)


if __name__ == "__main__":

    visitor = CSDNBlogVisitor()
    visitor.run()