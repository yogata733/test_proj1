from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin import AdminSite
from django.contrib import admin

# Register your models here.
from . import models

# 管理画面にUserモデルを登録
@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    pass
# 管理画面にYoutubeChannelモデルを登録
@admin.register(models.YoutubeChannel)
class YoutubeChannelAdmin(admin.ModelAdmin):
    pass


# 一般ユーザーが使えるもう一つの管理画面
class UserAdminSite(AdminSite):
    site_header = 'test-project'
    site_title = 'マイページ'
    index_title = 'マイページ'
    # 右サイドバーの最近行った操作を非表示にする (ホーム画面のパスを変更)
    index_template = 'admin/mypage/index.html'
    # 左サイドバーを非表示
    enable_nav_sidebar = False

    login_form = AuthenticationForm

    # アクティブユーザのログインを許可
    def has_permission(self, request):
        return request.user.is_active


# インスタンス生成
mypage_site = UserAdminSite(name="mypage")


'''
下記のように
ModelAdminを継承したUserAdminをさらに継承することで
メソッドをオーバーライドしたChangeUserAdminを
AdminSiteを継承したUserAdminSiteのインスタンスにモデルクラスを登録する際の第２引数に渡すと
ModelAdminとAdminSiteを組み合わせて使えるようだ。
（理由は分からない。デコレータで@mypage_site.register(models.User)を前につけたらエラーになった。）
'''


# 一般ユーザーのアカウント編集画面用のモデル
class ChangeUserAdmin(UserAdmin):
    # Userモデル編集画面のフォームをフィールドセッツで変更
    fieldsets = (
        (None, {'fields': ('user_id', 'username')}),
        ('個人情報', {'fields': ('email',)}),
    )
    readonly_fields = ('user_id',)
    # Userモデル一覧画面を表示しない (changelist_view()で使われるカスタムンテンプレートの絶対パスを変更)
    change_list_template = 'admin/ChangeUserAdmin/change_list.html'
    # Userモデル編集画面の表示を変更 (change_view()で使われるカスタムンテンプレートの絶対パスを変更)
    change_form_template = 'admin/ChangeUserAdmin/change_form.html'
    # Userモデル編集履歴画面を表示しない (history_view()で使われるカスタムンテンプレートの絶対パスを変更)
    object_history_template = 'admin/ChangeUserAdmin/object_history.html'

    # Userモデルの編集権限をカスタマイズ
    def has_change_permission(self, request, obj=None):
        has_perm = super().has_change_permission(request, obj)
        # モデル変更画面表示時・変更実行時 以外では obj の値は None
        if obj is None:
            return has_perm
        else:
            # Userモデルのidとログインユーザーのidが一致した場合のみ編集を許可
            return has_perm and obj.id == request.user.id

    # Userモデルのレコード詳細の参照を許可しない
    def has_view_permission(self, request, obj=None):
        return False

    # Userモデルをホーム画面に表示しない
    def has_module_permission(self, request, obj=None):
        return False


# UserAdminSiteのインスタンスmypage_siteにモデルクラスを登録する
mypage_site.register(models.User, ChangeUserAdmin)
