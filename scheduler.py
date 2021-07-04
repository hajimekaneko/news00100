from flask import Flask, request, abort
import os
import sys
import json
import datetime
import main
import random

try:
    import MySQLdb
except:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb

from argparse import ArgumentParser

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReplyButton, QuickReply, PostbackAction
from functions import Questions, Push

app = Flask(__name__)

ABS_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
REMOTE_HOST = os.environ['DB_HOST']
REMOTE_DB_NAME = os.environ['DB_DATABASE']
REMOTE_DB_USER = os.environ['DB_USERNAME']
REMOTE_DB_PASS = os.environ['DB_PASSWORD']

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
push = Push()
random = random.random()
now_time = datetime.datetime.now().time()

# 9:00~21:00に平均3回，ランダムなタイミングで実行 (herokuは10分に1回起動)
print("乱数 (0.0416666667以下で起動)："+str(random))
print("時間："+str(now_time))
if __name__ == "__main__" and random <= 3 / (6 * 12) and datetime.time(9) <= now_time <= datetime.time(21):
    # IDのDBからの取得
    try:
        conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME)
        c = conn.cursor()
        c.execute("SELECT `user_id` FROM `user`;")
    except Exception as e:
        print("エラー: " + str(e))
            
    user_ids = [item[0] for item in c.fetchall()]
    number = 1

    # 前回送信分の待機状態を解除 (新しく記録されないように)
    c.execute("UPDATE `monitor_results` SET `waiting`='FALSE' WHERE waiting='TRUE';")
    conn.commit()
    
    for user_id in user_ids:
        # プッシュメッセージ送信
        push.send_push_message(main.push_instruction, main.push_button, user_id)

        c.execute("SELECT `participant_id` FROM `user` WHERE `user_id` = '"+user_id+"';")
        participant_id = c.fetchall()[0][0]

        print(str(number) + "人目送信")
        print("ID: "+participant_id)
        number += 1

        # 送信時間を保存し，待機状態をオンにする
        c.execute("INSERT INTO `monitor_results` (`user_id`, `participant_id`, `sending`, `waiting`) VALUES ('"+user_id+"', '"+participant_id+"', '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"', 'TRUE');")
        conn.commit()
        
    conn.close()
    c.close()

else:
    print("NOT executed")