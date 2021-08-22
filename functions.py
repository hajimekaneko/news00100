import os
import datetime
from linebot import LineBotApi
from linebot.models import PostbackAction, QuickReplyButton, QuickReply, TextSendMessage, TemplateSendMessage, ButtonsTemplate

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

# プッシュ送信
class Push:
    # push_instruction: 教示，push_button: ボタン表示，user_id: LINE個人識別子
    def send_push_message(self, push_instruction, push_button, user_id=None):
        if user_id is None:
            return False
        line_bot_api.push_message(
            to=user_id,
            messages=TemplateSendMessage(
                alt_text=push_instruction,
                template=ButtonsTemplate(
                    text=push_instruction,
                    actions=[PostbackAction(label=push_button, data=push_button, display_text=push_button)]
                )
            )       
        )

# 質問項目
class Questions:

    def __init__(self, event):
        self.event = event

    # リッカート式
    # instruction: 教示，first_number: スケール開始数，point: 何件法か（デフォルトは7），pre_instruction: 教示の前にもう一言（任意）
    def ask_likert(self, instruction, first_number=1, point=7, pre_instruction=""):
        likert_scale = []
        for i in range(point):
            likert_scale.append(QuickReplyButton(
                action=PostbackAction(label=str(first_number), display_text=str(first_number), data=" ".join([instruction, str(first_number)]))))
            first_number += 1
        print(str(i+1) + "件法")
        if pre_instruction == "":
            line_bot_api.reply_message(self.event.reply_token, TextSendMessage(
                text=instruction, quick_reply=QuickReply(items=likert_scale)))
            first_number -= point
        else:
            line_bot_api.reply_message(self.event.reply_token, [TextSendMessage(
                text=pre_instruction), TextSendMessage(text=instruction, quick_reply=QuickReply(items=likert_scale))])
            first_number -= point


    # 多岐選択式
    # instruction: 教示，items_list: 選択項目（リスト型で）
    def ask_choices(self, instruction, items_list):
        quick_reply_buttons = []
        for item_name in items_list:
            quick_reply_buttons.append(QuickReplyButton(action=PostbackAction(
                label=str(item_name), display_text=str(item_name), data=" ".join([instruction, item_name]))))
        line_bot_api.reply_message(self.event.reply_token, TextSendMessage(
            text=instruction, quick_reply=QuickReply(items=quick_reply_buttons)))