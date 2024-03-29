from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.conf import settings
# フォーム保存完了時の認証メールを送信に必要
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
# ユーザ作成時に Permission を付与するために必要
from django.contrib.auth.models import Permission
# ユーザーモデルにアクセスする時にはfrom .models import Userなどではなく、必ずget_user_modelで取得する。
# 開発中にAUTH_USER_MODELが切り替わったときなどにエラーになるため。
User = get_user_model()

subject = "登録確認"
message_template = """
ご登録ありがとうございます。
以下URLをクリックして登録を完了してください。

"""


def get_activate_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return settings.FRONTEND_URL + "/activate/{}/{}/".format(uid, token)


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        # commit=Falseだと、DBに保存されない
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        # 確認するまでログイン不可にする
        user.is_active = False

        if commit:
            user.save()
            activate_url = get_activate_url(user)
            message = message_template + activate_url
            user.email_user(subject, message)
        return user


def activate_user(uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        return False

    if default_token_generator.check_token(user, token):
        # change_userパーミッションオブジェクトを取得
        permission_change = Permission.objects.get(
            codename='change_user')
        # userモデルにchange_userパーミッションを付与
        user.user_permissions.add(permission_change)

        user.is_active = True
        user.save()
        return True

    return False
