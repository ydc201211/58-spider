#!/usr/bin/python
# coding=utf-8
# 文件名：Tt.py

import requests
import re
import os
import time
import base64
from io import BytesIO
from fontTools.ttLib import TTFont

# 存储爬取信息的列表
g_info = list()
# 存储爬取的数字映射列表
glypth_dict = {}

min_price = 0
max_price = 0


def get_session():
    """获取一个设置了头部的session,自动保持cookie"""
    s = requests.Session()
    s.headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'zh-CN,zh;q=0.9',
        'referer': 'https://cq.58.com/zufang/?PGTID=0d100000-008c-78a5-ac77-a44cc3330ee8&ClickID=2',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
    }
    s.get(url='https://cq.58.com/zufang/')
    return s


def convert(s):
    """把&#x9201转换为转换为真正的数字"""
    s = s.strip('&#x;')  # 例如把'&#x957f;'变成'957f'
    s = str(get_num(int(s, 16)))  # 字符串转换成10进制整数
    return s


def make_font_file(base64_string: str):
    # 将base64编码的字体字符串解码成二进制模式
    bin_data = base64.decodebytes(base64_string.encode())
    with open('testotf.woff', 'wb') as f:
        f.write(bin_data)
    return bin_data


def convert_font_to_xml(bin_data):
    # BytesIO把一个二进制文件当成文件来操作
    font = TTFont(BytesIO(bin_data))
    font.saveXML("tes.xml")


def get_num(decode_num):
    """获取对应数字"""
    # ret_list = []
    # for char in string:
    #     decode_num = ord(char)
    #     num = glypth_arr[decode_num]
    #     num = int(num[-2:])-1
    #     ret_list.append(num)
    # return ret_list
    global glypth_dict
    num = glypth_dict[decode_num]
    num = int(num[-2:])-1
    return num


def get_arr(base64_str: str):
    """获取数字映射列表"""
    font = TTFont(BytesIO(make_font_file(base64_str)))
    # uniList = font['cmap'].tables[0].ttFont.getGlyphOrder()
    c = font['cmap'].tables[0].ttFont.tables['cmap'].tables[0].cmap
    # c = font.getBestCmap()
    global glypth_dict
    glypth_dict = c
    print('cmap is:::::', c)


def get_base64_str(html: str):
    """获取base64加密字符串"""
    base64_big_str = re.search(r'data:application/font-ttf;charset=utf-8;base64,.*?\'', html).group()
    base64_big_str = base64_big_str.replace('data:application/font-ttf;charset=utf-8;base64,', '')
    base64_big_str = base64_big_str.replace('\'', '')
    return base64_big_str


def get_content(html, info=g_info):
    """解析具体的网页，存入列表中"""
    # 诊断参数
    assert isinstance(html, str)
    if not info or not isinstance(info, list):
        info = g_info
    # 替换换行和&#x
    html = html.replace('\n', '')

    global min_price, max_price
    # 获取数字映射列表
    get_arr(get_base64_str(html))

    html = re.sub(r'&#x[a-f0-9]{4};', lambda match: convert(match.group()), html)
    # 获取li块列表
    ul = re.search(r'<ul class="listUl">(.*?)</ul>', html).group(1)
    lis = re.findall(r'<li logr=".*?"\s+sortid=".*?">(.*?)</li>', ul)
    # 遍历li块列表,取具体的内容,存入列表中, 解析出错会打印错误并继续执行
    for li in lis:
        try:
            temp = dict()
            temp['img'] = "https:" + re.search(r'<img\s+lazy_src="(.*?)"\s+src=".*?">', li).group(1)
            temp['name'] = re.search(r'<a href=".*?"\s+class="strongbox"\s+tongji_label="listclick".*?>\s*(.*?)\s*</a>', li).group(1)
            temp['money'] = re.search(r'<div class="money">\s*?<b class="strongbox">(.*?)</b>元/月\s*?</div>', li).group(1)
            ret = re.search(r'<p class="room strongbox">(.*?)\s+(&nbsp;)+(.*?)</p>', li)
            temp['house'] = ret.group(1) + ret.group(3)
            if  int(temp['money']) >= int(min_price) and int(temp['money']) <= int(max_price):
                info.append(temp)
        except Exception as err:
            print(err)


def save_content(info=g_info):
    """把列表里面的信息存入文件"""
    # 检测info列表
    if not info or not isinstance(info, list):
        info = g_info
    # 写入txt文件
    # with open('info.txt', 'a', encoding='utf-8') as f:
    #     temp = "标题:{}\n\t价位:{:<8}户型:{}\n"
    #     for i in info:
    #         temp2 = temp.format(i['name'], i['money'], i['house'])
    #         f.write(temp2)
    import json
    with open('info.json', 'w', encoding='utf-8') as f:
        # 写入json文件,中文字符串编码问题为\uxxxx这样显示
        # json.dump(info, f)
        # 可行的写入json文件方式
        f.write(json.dumps(info, ensure_ascii=False))


def get_img(session, imgdir=None, info=g_info):
    """通过爬取的图片链接，下载并保存图片"""
    # 诊断参数
    assert isinstance(session, requests.Session)
    if not info or not isinstance(info, list):
        info = g_info
    if not imgdir or not isinstance(imgdir, str) or (
            not os.path.isdir(imgdir) and not os.path.isdir(os.path.join('.', imgdir))):
        if not os.path.exists('./图片'):
            os.mkdir('./图片')
        imgdir = './图片'
    # 遍历下载图片
    for item in info:
        try:
            img = session.get(item['img']).content
            # 部分标题名称最后面为标点或者标题中含义/，不能成功存储,替换/,在后面放时间,使之成为有效路径
            filename = item['name'].replace('/', '-')
            filename += str(time.time()) + '.jpg'
            with open(os.path.join(imgdir, filename), 'wb') as f:
                f.write(img)
        except Exception as err:
            print(err)


def get_link(session, pindex=1,local_str='jiangbei'):
    """pindex为页码"""
    assert isinstance(session, requests.Session)

    url = 'https://cq.58.com/{}/zufang/0/j1/pn{}/?pgtid_=0d100000-008c-718c-36b7-c3b74bedbdd5&PGTID=0d300008-0002-8be1-3ca4-f60929035993&ClickID=2'.format(local_str,int(pindex))

    try:
        res = session.get(url=url)
        if res.status_code != 200:
            raise Exception('状态码非200')
        has_data = 'noresult-tip' in res.text
        if not has_data:
            get_content(res.text)
            return 'next'
        else:
            return 'no-data'
    except Exception as err:
        print(err)


def main():
    flag = '1'
    try:
        local_str = str(input("请输入爬取地区全拼(五里店、黄泥磅、大石坝、大竹林):"))
        global min_price, max_price
        range_price = input("请输入价格区间(例如:1000~5000):")
        range_price_list = range_price.split('~')
        min_price = range_price_list[0]
        max_price = range_price_list[1]
        pindex = 1
    except:
        pindex = 1

    s = get_session()
    while flag == '1':
        ret = get_link(session=s, pindex=pindex, local_str=local_str)
        if ret == 'no-data':
            flag = '0'
        pindex += 1
    get_img(session=s)
    save_content()



if __name__ == '__main__':
    main()