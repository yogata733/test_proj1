from django.shortcuts import redirect
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path
import pickle
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .models import User
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
        # コンテクストのresultにTrue/Falseの結果を渡します。
        return super().get(request, result=result, **kwargs)


# YouTubeのChannelIDを取得
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS_FILE = 'client_secrets.json'


def yt_get_authenticated_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
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
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def youtube(request):
    if request.method == 'POST':
        # YouTubeボタンがクリックされた場合
        if 'youtube' in request.POST:
            yt = yt_get_authenticated_service()
            # 登録しているチャンネル情報について取得する。
            # フィルタとして mine を True にすると、自分が持っているチャンネルのみ取得することができる。
            subscriptions = yt.subscriptions().list(
                part='snippet',
                mine=True,
                fields='items(snippet(title,resourceId(channelId)))'
            ).execute()
            subscription = subscriptions['items'][0]  # チャンネル数は、とりあえずの0固定
            snippet = subscription['snippet']
            resourceId = snippet['resourceId']
            # ログインユーザーと一致するユーザーのyoutube_idを更新
            User.objects.filter(id=request.user.id).update(
                youtube_id=resourceId['channelId'])
            # ホーム画面にリダイレクトする
            return redirect('index')
