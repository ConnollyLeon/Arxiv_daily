# -*- coding: utf-8 -*-
"""
Created on Sat Jul 14 14:24:58 2018

Edited by Liang Peng on Thu Nov 18 09:38:39 2021
@author: ZZH, Liang Peng
"""

import requests
import time
import pandas as pd
from bs4 import BeautifulSoup
from collections import Counter
import os
import random

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule

# Global Constants

# 下载文章的路径
arxiv_path = '/home/connolly/Documents/arxiv'
# 发送者邮箱
sender = 'yourqq@qq.com'
# 发送者的登陆用户名和密码
user = 'yourqq@qq.com'
password = 'balabala'  # qq的在网页版邮箱设置里找，需要生成
# 发送者邮箱的SMTP服务器地址
smtpserver = 'smtp.qq.com'
# 接收者的邮箱地址
receiver = 'youremail@qq.com'  # receiver 可以是一个list


def get_one_page(url):
    response = requests.get(url)
    print(response.status_code)
    while response.status_code == 403:
        time.sleep(500 + random.uniform(0, 500))
        response = requests.get(url)
        print(response.status_code)
    print(response.status_code)
    if response.status_code == 200:
        return response.text

    return None


def send_email(title, content):
    msg = MIMEMultipart('alternative')

    part1 = MIMEText(content, 'plain', 'utf-8')
    # html = open('subject_file.html','r')
    # part2 = MIMEText(html.read(), 'html')

    msg.attach(part1)
    # msg.attach(part2)

    # 发送邮箱地址
    msg['From'] = sender
    # 收件箱地址
    msg['To'] = receiver
    # 主题
    msg['Subject'] = title

    smtp = smtplib.SMTP_SSL(smtpserver, 465)  # 实例化SMTP_SSL对象, 填入服务器和端口号, qq邮箱的port为465
    smtp.login(user, password)  # 登陆smtp服务器
    smtp.sendmail(sender, receiver, msg.as_string())  # 发送邮件 ，这里有三个参数
    '''
    login()方法用来登录SMTP服务器，sendmail()方法就是发邮件，由于可以一次发给多个人，所以传入一个list，邮件正文
    是一个str，as_string()把MIMEText对象变成str。
    '''
    smtp.quit()


def download_papers(selected_pp):
    if not os.path.exists(arxiv_path + 'selected/' + time.strftime("%Y-%m-%d")):
        os.makedirs(arxiv_path + 'selected/' + time.strftime("%Y-%m-%d"))
    for selected_paper_id, selected_paper_title in zip(selected_pp['id'], selected_pp['title']):
        selected_paper_id = selected_paper_id.split(':', maxsplit=1)[1]
        selected_paper_title = selected_paper_title.split(':', maxsplit=1)[1]
        r = requests.get('https://arxiv.org/pdf/' + selected_paper_id)
        while r.status_code == 403:
            time.sleep(500 + random.uniform(0, 500))
            r = requests.get('https://arxiv.org/pdf/' + selected_paper_id)
        selected_paper_id = selected_paper_id.replace(".", "_")
        pdfname = selected_paper_title.replace("/", "_")  # pdf名中不能出现/和：
        pdfname = pdfname.replace("?", "_")
        pdfname = pdfname.replace("\"", "_")
        pdfname = pdfname.replace("*", "_")
        pdfname = pdfname.replace(":", "_")
        pdfname = pdfname.replace("\n", "")
        pdfname = pdfname.replace("\r", "")
        print(arxiv_path + 'selected/' + time.strftime("%Y-%m-%d") + '/%s %s.pdf' % (
            selected_paper_id, selected_paper_title))
        with open(arxiv_path + 'selected/' + time.strftime("%Y-%m-%d") + '/%s %s.pdf' % (
                selected_paper_id, pdfname), "wb") as code:
            code.write(r.content)


def fetch_arxiv(url, key_ws, send_email_flag):
    html = get_one_page(url)
    soup = BeautifulSoup(html, features='html.parser')
    content = soup.dl
    list_ids = content.find_all('a', title='Abstract')
    list_title = content.find_all('div', class_='list-title mathjax')
    list_authors = content.find_all('div', class_='list-authors')
    list_subjects = content.find_all('div', class_='list-subjects')
    list_subject_split = []
    for subjects in list_subjects:
        subjects = subjects.text.split(': ', maxsplit=1)[1]
        subjects = subjects.replace('\n\n', '')
        subjects = subjects.replace('\n', '')
        subject_split = subjects.split('; ')
        list_subject_split.append(subject_split)

    items = []
    for i, paper in enumerate(zip(list_ids, list_title, list_authors, list_subjects, list_subject_split)):
        items.append([paper[0].text, paper[1].text, paper[2].text, paper[3].text, paper[4]])
    name = ['id', 'title', 'authors', 'subjects', 'subject_split']
    paper = pd.DataFrame(columns=name, data=items)
    paper.to_csv(
        arxiv_path + '' + time.strftime("%Y-%m-%d") + '_' + str(len(items)) + '.csv')

    '''subject split'''
    subject_all = []
    for subject_split in list_subject_split:
        for subject in subject_split:
            subject_all.append(subject)
    subject_cnt = Counter(subject_all)
    # print(subject_cnt)
    subject_items = []
    for subject_name, times in subject_cnt.items():
        subject_items.append([subject_name, times])
    subject_items = sorted(subject_items, key=lambda subject_items: subject_items[1], reverse=True)
    name = ['name', 'times']
    subject_file = pd.DataFrame(columns=name, data=subject_items)
    # subject_file = pd.DataFrame.from_dict(subject_cnt, orient='index')
    subject_file.to_csv(
        arxiv_path + 'sub_cnt/' + time.strftime("%Y-%m-%d") + '_' + str(len(items)) + '.csv')
    # subject_file.to_html('subject_file.html')

    '''key_word selection'''
    selected_papers = paper[paper['title'].str.contains(key_ws[0], case=False)]
    for key_word in key_ws[1:]:
        selected_paper1 = paper[paper['title'].str.contains(key_word, case=False)]
        selected_papers = pd.concat([selected_papers, selected_paper1], axis=0)
    selected_papers.to_csv(arxiv_path + 'selected/' + time.strftime("%Y-%m-%d") + '_' + str(
        len(selected_papers)) + '.csv')

    '''send email'''
    content = 'Today arxiv has {} new papers in CS.DC area\n\n'.format(
        len(list_title), subject_cnt['Computer Vision and Pattern Recognition (cs.CV)'], len(selected_papers))
    content += 'Ensure your keywords is ' + str(key_ws) + '(case=True). \n\n'
    content += 'This is your paperlist.Enjoy! \n\n'
    for i, selected_paper in enumerate(zip(selected_papers['id'], selected_papers['title'], selected_papers['authors'],
                                           selected_papers['subject_split'])):
        # print(content1)
        content1, content2, content3, content4 = selected_paper
        content += '------------' + str(i + 1) + '------------\n' + content1 + content2 + str(content4) + '\n'
        content1 = content1.split(':', maxsplit=1)[1]
        content += 'https://arxiv.org/abs/' + content1 + '\n\n'

    content += 'Here is the Research Direction Distribution Report. \n\n'
    for subject_name, times in subject_items:
        content += subject_name + '   ' + str(times) + '\n'
    title = time.strftime("%Y-%m-%d") + ' you have {} papers'.format(len(selected_papers))
    if send_email_flag:
        send_email(title, content)
    f_report = open(arxiv_path + 'report/' + title + '.txt', 'w')
    f_report.write(content)
    f_report.close()

    '''dowdload key_word selected papers'''
    download_papers(selected_papers)


if __name__ == '__main__':
    # you can replace cs.DC with other fields.
    field = 'cs.DC'
    url = 'https://arxiv.org/list/' + field + '/pastweek?show=1000'

    # fill your key_words here
    key_words = ['parallel', 'parallelism', 'distributed', 'framework', 'large-scale']

    # Whether to send_email
    send_email_flag = True

    # Download papers to arxiv_path according to key_words
    fetch_arxiv(url, key_words, send_email_flag)

    # set daily fetch
    schedule.every().day.at("8:00").do(fetch_arxiv, url, key_words, send_email_flag)
    while True:
        schedule.run_pending()
