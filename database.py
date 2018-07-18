# -*- coding: utf-8 -*-

# @Author: yooongchun
# @File: database.py
# @Time: 2018/6/19
# @Contact: yooongchun@foxmail.com
# @blog: https://blog.csdn.net/zyc121561
# @Description: 数据库

import sqlite3
import time


class IPPool(object):
    """存取IP的数据库"""

    def __init__(self, database_name):
        self.__table_name = "ip_table"
        self.__database_name = database_name

    def __push(self, ip):
        '''存储IP，传入一个列表，格式为[[IP,PORT,ADDRESS,TYPE,PROTOCOL],...]'''
        conn = sqlite3.connect(self.__database_name, isolation_level=None)
        conn.execute(
            "create table if not exists %s(IP CHAR(20) UNIQUE, PORT INTEGER,ADDRESS CHAR(50),TYPE CHAR(50),PROTOCOL CHAR(50))"
            % self.__table_name)
        for one in ip:
            conn.execute(
                "insert or ignore into %s(IP,PORT,ADDRESS,TYPE,PROTOCOL) values (?,?,?,?,?)"
                % (self.__table_name),
                (one[0], one[1], one[2], one[3], one[4]))
        conn.commit()
        conn.close()

    def push(self, ip, re_try_times=1):
        '''保存数据到数据库，为应对多线程，多进程的并发访问，采用多次重试模式'''
        if not isinstance(ip, list):
            return
        if not isinstance(re_try_times, int) or re_try_times < 1:
            re_try_times = 1
        for i in range(re_try_times):
            try:
                self.__push(ip)
                return True
            except Exception:
                time.sleep(0.05)
                continue
        return False

    def __pull(self, random_flag=False):
        '''获取IP，返回一个列表'''
        conn = sqlite3.connect(self.__database_name, isolation_level=None)
        conn.execute(
            "create table if not exists %s(IP CHAR(20) UNIQUE, PORT INTEGER,ADDRESS CHAR(50),TYPE CHAR(50),PROTOCOL CHAR(50))"
            % self.__table_name)
        cur = conn.cursor()
        if random_flag:
            cur.execute("select * from %s order by random() limit 1" %
                        self.__table_name)
            response = cur.fetchone()
        else:
            cur.execute("select * from %s" % self.__table_name)
            response = cur.fetchall()
        cur.close()
        conn.close()
        return response

    def pull(self, re_try_times=1, random_flag=False):
        '''取数据从数据库，为应对多线程，多进程的并发访问，采用多次重试模式'''
        if not isinstance(random_flag, bool):
            random_flag = False
        if not isinstance(re_try_times, int) or re_try_times < 1:
            re_try_times = 1
        for i in range(re_try_times):
            try:
                ip = self.__pull(random_flag=random_flag)
                return ip
            except Exception:
                time.sleep(0.05)
                continue
        return False

    def __delete(self, IP=None):
        '''删除指定的记录'''
        conn = sqlite3.connect(self.__database_name, isolation_level=None)
        conn.execute(
            "create table if not exists %s(IP CHAR(20) UNIQUE, PORT INTEGER,ADDRESS CHAR(50),TYPE CHAR(50),PROTOCOL CHAR(50))"
            % self.__table_name)
        cur = conn.cursor()
        if IP is not None:
            cur.execute("delete from %s where IP=?" % self.__table_name,
                        (IP[0], ))
        else:
            cur.execute("delete from %s" % self.__table_name)
        cur.close()
        conn.close()

    def delete(self, re_try_times=1, IP=None):
        '''删除数据从数据库，为应对多线程，多进程的并发访问，采用多次重试模式'''
        if IP is None:
            return False
        if not isinstance(re_try_times, int) or re_try_times < 1:
            re_try_times = 1
        for i in range(re_try_times):
            try:
                self.__delete(IP)
                return True
            except Exception:
                time.sleep(0.05)
                continue
        return False


class InfoPool(object):
    """
    存取博客文章统计数据的数据库
    """

    def __init__(self, database_name):
        self.__table_name = "info_table"
        self.__database_name = database_name

    def push(self, info):
        '''存储统计信息，传入一个列表，格式为[[TIME,TIMESTAMP,ARTICLE_NUM,TOTAL_VISIT],...]'''
        if not isinstance(info, list) or len(info) < 1:
            return
        try:
            conn = sqlite3.connect(self.__database_name, isolation_level=None)
            conn.execute(
                "create table if not exists %s(TIME CHAR(50) UNIQUE,TIMESTAMP INTEGER,ARTICLE_NUM INTEGER,TOTAL_VISIT INTEGER)"
                % self.__table_name)
        except Exception:
            return False
        for one in info:
            if len(one) < 4:
                continue
            try:
                conn.execute(
                    "insert or ignore into %s(TIME,TIMESTAMP,ARTICLE_NUM,TOTAL_VISIT) values (?,?,?,?)"
                    % (self.__table_name), (one[0], one[1], one[2], one[3]))
            except Exception:
                continue
        conn.commit()
        conn.close()
        return True

    def pull(self):
        '''获取数据库内容，返回一个列表'''
        try:
            conn = sqlite3.connect(self.__database_name, isolation_level=None)
            conn.execute(
                "create table if not exists %s(TIME CHAR(50) UNIQUE,TIMESTAMP INTEGER,ARTICLE_NUM INTEGER,TOTAL_VISIT INTEGER)"
                % self.__table_name)
        except Exception:
            return
        try:
            cur = conn.cursor()
            cur.execute("select * from %s" % self.__table_name)
            response = cur.fetchall()
            cur.close()
            conn.close()
        except Exception:
            return False
        return response

    def delete(self, TIME=None):
        '''删除指定的记录'''
        try:
            conn = sqlite3.connect(self.__database_name, isolation_level=None)
            conn.execute(
                "create table if not exists %s(TIME CHAR(50) UNIQUE,TIMESTAMP INTEGER,ARTICLE_NUM INTEGER,TOTAL_VISIT INTEGER)"
                % self.__table_name)
        except Exception:
            return
        cur = conn.cursor()
        if TIME is not None:
            try:
                cur.execute("delete from %s where TIME=?" % self.__table_name,
                            (TIME, ))
            except Exception:
                return False
        else:
            try:
                cur.execute("delete from %s" % self.__table_name)
            except Exception:
                return False
        cur.close()
        conn.close()
        return True


if __name__ == "__main__":
    pool = IPPool("IP.db")
    for index, ip in enumerate(pool.pull()):
        print(index, ip)
    print("-.-" * 20)