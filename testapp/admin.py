from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin import AdminSite
from django.contrib import admin

# Register your models here.
from . import models

# 管理画面にUserモデルを登録
@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    pass


# 一般ユーザーが使えるもう一つの管理画面
class UserAdminSite(AdminSite):
    site_header = 'マイページ'
    site_title = 'マイページ'
    index_title = 'ホーム'
    site_url = None
    login_form = AuthenticationForm

    def has_permission(self, request):
        return request.user.is_active


mypage_site = UserAdminSite(name="mypage")

'''
下記のように
ModelAdminを継承したUserAdminをさらに継承してメソッドをオーバーライドしたChangeUserAdminを
AdminSiteを継承したUserAdminSiteのインスタンスにモデルクラスを登録する際の第２引数に渡すと
ModelAdminとAdminSiteを組み合わせて使えるようだ。
（理由は分からない。デコレータで@mypage_site.register(models.User)を前につけたらエラーになった。）
'''


class ChangeUserAdmin(UserAdmin):
    def has_change_permission(self, request, obj=None):
        has_perm = super().has_change_permission(request, obj)
        # モデル変更画面表示時・変更実行時 以外では obj の値は None
        if obj is None:
            return has_perm
        else:
            return has_perm and obj.id == request.user.id

    def has_view_permission(self, request, obj=None):
        return False


mypage_site.register(models.User, ChangeUserAdmin)
