from django.urls import path
from . import views

app_name = 'psys'

urlpatterns = [
    # トップ画面
    path('', views.Index, name='Index'),

    # 認証
    path('Login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),

    # メニュー
    path('MainMenu', views.MainMenu, name='MainMenu'),
    path('CustomerManagementMenu', views.CustomerManagementMenu, name='CustomerManagementMenu'),

    # 得意先管理
    path('CustomerList', views.CustomerList, name='CustomerList'),
    path('CustomerSearch', views.CustomerSearch, name='CustomerSearch'),
    path('CustomerRegist', views.CustomerRegist, name='CustomerRegist'),
    path('CustomerDelete', views.CustomerDelete, name='CustomerDelete'),
    path('CustomerDeleteResult', views.CustomerDeleteResult, name='CustomerDeleteResult'),
    path('CustomerUpdate', views.CustomerUpdate, name='CustomerUpdate'),
    path('CustomerUpdateResult', views.CustomerUpdateResult, name='CustomerUpdateResult'),

    # 得意先別集計
    path('OrderSummaryMenu', views.OrderSummaryMenu, name='OrderSummaryMenu'),
    path('MonthlyOrderSummary', views.MonthlyOrderSummary, name='MonthlyOrderSummary'),
    path('YearlyOrderSummary', views.YearlyOrderSummary, name='YearlyOrderSummary'),
    path('ItemOrderSummary', views.ItemOrderSummary, name='ItemOrderSummary'),

    # 従業員新規登録
    path('EmployeeRegist', views.EmployeeRegist, name='EmployeeRegist'),
]