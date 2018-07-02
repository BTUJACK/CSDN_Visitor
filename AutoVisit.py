# -*- coding: utf-8 -*-

# @Author: yooongchun
# @File: AutoVisit.py
# @Time: 2018/6/19
# @Contact: yooongchun@foxmail.com
# @blog: https://blog.csdn.net/zyc121561
# @Description: 程序入口

from ProxyIP import Crawl, Validation
from BlogVisitor import CSDNBlogVisitor
from multiprocessing import Process


def main():
    blogger = "zyc121561"
    # 初始化
    crawl = Crawl()
    validation = Validation()
    visitor = CSDNBlogVisitor(bolgger=blogger)
    # 启动
    pro1 = Process(target=crawl.run)  # 抓取代理IP
    pro2 = Process(target=validation.run)  # 定期校验代理IP
    pro3 = Process(target=visitor.run)  # 访问博客
    pro1.start()
    pro2.start()
    pro3.start()
    pro1.join()
    pro2.join()
    pro3.join()


if __name__ == "__main__":
    main()
