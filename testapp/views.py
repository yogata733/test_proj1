from django.shortcuts import redirect
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path
import pickle
import gc
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .models import User, YoutubeChannel
from .forms import SignUpForm
# 認証OKの場合にユーザーを有効化するために必要
from django.views.generic import TemplateView
from .forms import activate_user


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


# 認証確認用ビュー
class ActivateView(TemplateView):
    template_name = "registration/activate.html"

    def get(self, request, uidb64, token, *args, **kwargs):
        # 認証トークンを検証して、
        result = activate_user(uidb64, token)
        # コンテクストのresultにTrue/Falseの結果を渡す。
        return super().get(request, result=result, **kwargs)


# YouTube DATA APIの実行のための変数
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS_FILE = 'client_secrets.json'


# Youtubeの認証
def yt_get_authenticated_service(uid):
    creds = None
    token_name = 'token/' + str(uid) + '.pickle'
    # The file token/uid.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_name):
        with open(token_name, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_name, 'wb') as token:
            pickle.dump(creds, token)
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


# Youtubeの情報更新
def yt_update(request):
    user = User.objects.get(id=request.user.id)
    # 一旦、自分のチャンネルと登録チャンネルを連携解除(全件削除)する
    user.yt_channels.clear()
    user.yt_subscriptions.clear()
    yt = yt_get_authenticated_service(request.user.id)
    # 自分のチャンネルがあれば、そのチャンネル情報を取得し更新する。
    # フィルタとして mine を True にすると、自分が持っているチャンネルのみ取得することができる。
    channels = yt.channels().list(
        part='snippet,statistics',
        mine=True,
        fields='items(id,snippet(title,description),statistics(subscriberCount))'
    ).execute()
    # 自分のチャンネルを持っている場合
    if 'items' in channels:
        # 各チャンネル情報を取り出す
        for channel in channels['items']:
            ch_snippet = channel['snippet']
            ch_statistics = channel['statistics']
            # チャンネルが登録者数を公表している場合、登録者数を登録する。
            if 'subscriberCount' in ch_statistics:
                ch_subscriberCount = ch_statistics['subscriberCount']
            # チャンネルが登録者数を公表していない場合、登録者数を-1とする。
            else:
                ch_subscriberCount = -1
            # 既に自分のチャンネル情報が登録されていれば更新し、登録されていなければ登録する。
            ch_ytch, ch_created = YoutubeChannel.objects.update_or_create(
                channelid=channel['id'],
                defaults={
                    'title': ch_snippet['title'],
                    'description': ch_snippet['description'],
                    'subscriberCount': ch_subscriberCount
                })
            # 変数を削除する。
            del channel
            # Userのyt_channels(ManyToManyField)に紐付ける。
            user.yt_channels.add(ch_ytch)
            # 変数を削除する。
            del ch_snippet, ch_statistics, ch_subscriberCount, ch_ytch, ch_created
    # 変数を削除する。
    del channels

    # ここからは登録チャンネルの情報を取得し更新する処理
    sub_page_token = ''
    sub_channelId_list = []
    # 登録チャンネルは１ページ毎に5結果しか取得できないため、
    # nextPageTokenがなくなるまで繰り返し、全件取得する。
    while sub_page_token != 'end_page':
        # 登録しているチャンネル情報を取得する。
        subscriptions = yt.subscriptions().list(
            part='snippet',
            mine=True,
            maxResults=50,
            pageToken=sub_page_token,
            fields='items(snippet(title,description,resourceId(channelId))),nextPageToken'
        ).execute()
        # 各チャンネル情報を取り出す
        for subscription in subscriptions['items']:
            sub_snippet = subscription['snippet']
            # 変数を削除しメモリを解放する。
            del subscription
            sub_resourceId = sub_snippet['resourceId']
            # 下で登録チャンネルの登録者数を更新するためのリスト作成。
            sub_channelId_list.append(sub_resourceId['channelId'])
            # 既にチャンネル情報が登録されていれば更新し、登録されていなければ登録する。
            sub_ytch, sub_created = YoutubeChannel.objects.update_or_create(
                channelid=sub_resourceId['channelId'],
                defaults={
                    'title': sub_snippet['title'],
                    'description': sub_snippet['description'],
                    'subscriberCount': -2   # とりあえずnullにしないため。下で改めて更新する。
                })
            # Userのyt_subscriptions(ManyToManyField)に紐付ける。
            user.yt_subscriptions.add(sub_ytch)
            # 変数を削除しメモリを解放する。
            del sub_snippet, sub_resourceId, sub_ytch, sub_created
        # nextPageTokenを取得する。(nextPageTokenが無ければ終わる)
        if 'nextPageToken' in subscriptions:
            sub_page_token = subscriptions['nextPageToken']
        else:
            sub_page_token = 'end_page'
        # 変数を削除する。
        del subscriptions

    # ここからは登録チャンネルの登録者数を更新する処理。
    # (APIを叩く回数を減らすためにループの外に出す)
    i = 0
    b = []
    sub_channelId_joinlist = []
    # 一度に50件しか取得できないため、channelIdを50件ずつジョイントしてリストに入れる。
    for a in sub_channelId_list:
        b.append(a)
        i += 1
        if i == 50:
            sub_channelId_joinlist.append(','.join(b))
            i = 0
            b.clear()
        # 変数を削除しメモリを解放する。
        del a
    sub_channelId_joinlist.append(','.join(b))
    # 変数を削除する。
    del sub_channelId_list
    # 50件ずつ取得する。
    for sub_channelId_join in sub_channelId_joinlist:
        # 登録チャンネルの情報を取得する。
        subscription_ch = yt.channels().list(
            part='snippet,statistics',
            id=sub_channelId_join,
            fields='items(id,statistics(subscriberCount))'
        ).execute()
        # 変数を削除しメモリを解放する。
        del sub_channelId_join
        # 各登録チャンネルのIDと登録者数を取り出す。
        for subch_items in subscription_ch['items']:
            subch_channelId = subch_items['id']
            subch_statistics = subch_items['statistics']
            # 変数を削除しメモリを解放する。
            del subch_items
            # チャンネルが登録者数を公表している場合、登録者数を登録する。
            if 'subscriberCount' in subch_statistics:
                subch_subscriberCount = subch_statistics['subscriberCount']
            # チャンネルが登録者数を公表していない場合、登録者数を-1とする。
            else:
                subch_subscriberCount = -1
            # 各登録チャンネルの登録者数を更新する。
            YoutubeChannel.objects.filter(
                channelid=subch_channelId).update(
                subscriberCount=subch_subscriberCount)
            # 変数を削除しメモリを解放する。
            del subch_channelId, subch_subscriberCount
    # 変数を削除する。
    del sub_channelId_joinlist


# Youtubeボタンクリック時処理
def yt_update_button(request):
    # YouTube情報更新ボタンがクリックされた場合
    if request.method == 'POST':
        if 'yt_update_button' in request.POST:
            yt_update(request)
    # ホーム画面にリダイレクトする
    return redirect('index')


# Youtubeの連携解除
def yt_delete(request):
    uid = request.user.id
    token_name = 'token/' + str(uid) + '.pickle'
    # アクセストークンがあればファイルを削除する
    if os.path.exists(token_name):
        os.remove(token_name)
    user = User.objects.get(id=request.user.id)
    # 自分のチャンネルを連携解除(全件削除)する
    user.yt_channels.clear()
    # 登録しているチャンネルを連携解除(全件削除)する
    user.yt_subscriptions.clear()


# Youtube連携解除ボタンクリック時処理
def yt_delete_button(request):
    # YouTube情報更新ボタンがクリックされた場合
    if request.method == 'POST':
        if 'yt_delete_button' in request.POST:
            yt_delete(request)
    # ホーム画面にリダイレクトする
    return redirect('index')
