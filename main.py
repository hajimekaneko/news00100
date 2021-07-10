import os
import sys
import json
import datetime

try:
    import MySQLdb
except:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb

from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import FollowEvent, MessageEvent, PostbackEvent, PostbackAction, TextMessage, QuickReplyButton, MessageAction, QuickReply, TextSendMessage, TemplateSendMessage, ButtonsTemplate
from functions import Questions

app = Flask(__name__)

ABS_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
REMOTE_HOST = os.environ['DB_HOST']
REMOTE_DB_NAME = os.environ['DB_DATABASE']
REMOTE_DB_USER = os.environ['DB_USERNAME']
REMOTE_DB_PASS = os.environ['DB_PASSWORD']

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# 友達登録時の動作
@handler.add(FollowEvent)
def on_follow(event):
    reply_token = event.reply_token
    user_id = event.source.user_id

    # LINEユーザー識別子のDBへの保存
    try:
        conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME)
        c = conn.cursor()
        sql = "SELECT `id` FROM `user` WHERE `user_id` = '"+user_id+"';"
        c.execute(sql)
        ret = c.fetchall()
        if len(ret) == 0:
            sql = "INSERT INTO `user` (`user_id`) VALUES ('"+user_id+"');"
        c.execute(sql)
        conn.commit()
    except Exception as e:
        print("エラー: " + str(e))
    finally:
        conn.close()
        c.close()

    # メッセージの送信
    line_bot_api.reply_message(reply_token=reply_token, messages=TextSendMessage('登録ありがとうございます！'))

# PUSH通知の教示
push_instruction = "モニタリングしませんか？ (ボタンは90分間有効です)"

# PUSH通知のボタン
push_button = "モニタリング開始"

# 以下，アプリ動作の実装

# 文字入力に反応して起こるアクション
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    question = Questions(event)
    user_id = event.source.user_id
    text = event.message.text

    try:
        conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME)
        c = conn.cursor()
        c.execute("SELECT `id_prompt` FROM `user` WHERE `user_id` = '"+user_id+"';")
        id_prompt = c.fetchall()
    except Exception as e:
        print("エラー: " + str(e))

    # テスト
    if "テスト起動" == text:
        c.execute("UPDATE `monitor_results` SET `waiting`='FALSE' WHERE waiting='TRUE';")
        conn.commit()
        line_bot_api.reply_message(
            event.reply_token,
            TemplateSendMessage(
                alt_text=push_instruction,
                template=ButtonsTemplate(
                    text=push_instruction,
                    actions=[PostbackAction(label=push_button, data=push_button, display_text=push_button)]
                )
            )
        )           
        c.execute("SELECT `participant_id` FROM `user` WHERE `user_id` = '"+user_id+"';")
        participant_id = c.fetchall()[0][0]
        c.execute("INSERT INTO `monitor_results` (`user_id`, `participant_id`, `sending`, `waiting`) VALUES ('"+user_id+"', '"+participant_id+"', '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"', 'TRUE');")
        conn.commit()

    # 参加者ID登録 step 1
    elif "ID" == text or "id" == text or "Id" == text:
        question.ask_choices("ID登録を開始しますか？", ["開始する", "やめる"])

    # 参加者ID登録 step 3
    # 参加者ID入力モードかどうかを判断
    elif id_prompt[0][0] == "TRUE":
        c.execute("UPDATE `user` SET `participant_id`='"+text+"' WHERE user_id='"+user_id+"';")
        # 参加者ID入力モードを解除
        c.execute("UPDATE user SET id_prompt = 'FALSE' WHERE user_id ='"+user_id+"';")

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="「"+text+"」がIDとして登録されました。"))
        
        conn.commit()
        conn.close()
        c.close()

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='登録されていない文字列です。'))

# ボタン押下に反応して起こるアクション
@handler.add(PostbackEvent)
def on_postback(event):
    question = Questions(event)
    user_id = event.source.user_id
    postback_data = event.postback.data
    pre_instruction = event.postback.data.split()[0]
    user_response = ""

    if len(postback_data.split()) == 2:
        user_response = event.postback.data.split()[1]

    ninety_minutes = datetime.timedelta(minutes=90)

    try:
        conn = MySQLdb.connect(user=REMOTE_DB_USER, passwd=REMOTE_DB_PASS, host=REMOTE_HOST, db=REMOTE_DB_NAME)
        c = conn.cursor()
    except Exception as e:
        print("エラー: " + str(e))    

    # 参加者ID登録 step 2
    if "開始する" == user_response:
        # 参加者ID入力モード開始
        c.execute("UPDATE user SET id_prompt = 'TRUE' WHERE user_id ='"+user_id+"';")
        conn.commit()
        conn.close()
        c.close()
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="IDを入力してください。",
            ))

    if "モニタリング開始" == postback_data:
        c.execute("SELECT `sending` FROM `monitor_results` WHERE `user_id` = '"+user_id+"' AND waiting='TRUE';")
        sending = c.fetchall()[0][0]

        # 通知から90分以内に反応した場合 (モニタリングを開始する)
        if datetime.datetime.now() <= sending + ninety_minutes:
            # リッカート式 1
            question.ask_likert(instruction="うれしい", pre_instruction="次の気分・感情をどの程度感じていますか？ (1:全く感じない～7:とても感じる)")
            c.execute("UPDATE `monitor_results` SET `responding` = '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"' WHERE user_id ='"+user_id+"' AND waiting = 'TRUE';")

        # 通知から90分経過した場合 (モニタリングを開始しない)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="90分経過したため通知が無効になりました。次回の通知をお待ちください。"))
    # リッカート式 2 (5件法)
    elif "うれしい" == pre_instruction:
        question.ask_likert(instruction="かなしい", point=5)
        c.execute("UPDATE `monitor_results` SET `うれしい` = '"+user_response+"' WHERE user_id ='"+user_id+"' AND waiting = 'TRUE';")
    # リッカート式 3 (-3開始)
    elif "かなしい" == pre_instruction:
        question.ask_likert(instruction="今の体調はどうですか？(-3:とても悪い～3:とても良い)", first_number=-3)
        c.execute("UPDATE `monitor_results` SET `かなしい` = '"+user_response+"' WHERE user_id ='"+user_id+"' AND waiting = 'TRUE';")
    # 多岐選択式 1
    elif "今の体調はどうですか？(-3:とても悪い～3:とても良い)" == pre_instruction:
        question.ask_choices(instruction="いま、だれかといますか？", items_list=["家族", "友だち", "同僚", "その他の人", "1人でいる"])
        c.execute("UPDATE `monitor_results` SET `現在の体調` = '"+user_response+"' WHERE user_id ='"+user_id+"' AND waiting = 'TRUE';")
    # 多岐選択式 2
    elif "いま、だれかといますか？" == pre_instruction:
        question.ask_choices(instruction="いま、なにをしていますか？", items_list=["仕事／勉強", "食べる／飲む", "余暇", "その他", "何もしていない"])
        c.execute("UPDATE `monitor_results` SET `一緒にいる人` = '"+user_response+"' WHERE user_id ='"+user_id+"' AND waiting = 'TRUE';")
    # 完了
    elif "いま、なにをしていますか？" == pre_instruction:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="モニタリングが完了しました！"))
        c.execute("UPDATE `monitor_results` SET `今していること` = '"+user_response+"', `finish` = '"+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"' WHERE user_id ='"+user_id+"' AND waiting = 'TRUE';")

    conn.commit()
    conn.close()
    c.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)