from django.test import TestCase, Client
from django.urls import reverse
from django.db import connection
from psys.models import Customer, CustomerNumbering, Employee, Orders, OrderDetails, Item


class PsysBaseTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'customer'")
            if not cursor.fetchone():
                with open('psysdb.sql', 'r', encoding='cp932') as f:
                    statements = f.read().split(';')
                for stmt in statements:
                    clean_lines = []
                    for line in stmt.splitlines():
                        l = line.strip()
                        if not l.startswith('--') and not l.startswith('/*') and not l.endswith('*/'):
                            clean_lines.append(line)
                    clean_stmt = ' '.join(clean_lines).strip()
                    if clean_stmt and not clean_stmt.lower().startswith(('drop database', 'create database', 'use ')):
                        try:
                            cursor.execute(clean_stmt)
                        except Exception:
                            pass

    def setUp(self):
        self.client = Client()

    def login_as_employee(self):
        """テスト用のログイン状態を作成"""
        session = self.client.session
        session['employee_no'] = 'R20001'
        session['employee_name'] = '鈴木一郎'
        session.save()


class IndexAndAuthTests(PsysBaseTestCase):
    def test_index_page(self):
        response = self.client.get(reverse('psys:Index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "販売支援システム")
        self.assertContains(response, "ログイン")

    def test_login_page_renders(self):
        response = self.client.get(reverse('psys:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "従業員番号")
        self.assertContains(response, "パスワード")

    def test_login_success(self):
        response = self.client.post(reverse('psys:login'), {
            'Employee_no': 'R20001',
            'password': 'ry000001'
        })
        self.assertRedirects(response, reverse('psys:MainMenu'))
        self.assertEqual(self.client.session['employee_no'], 'R20001')

    def test_login_failure(self):
        response = self.client.post(reverse('psys:login'), {
            'Employee_no': 'R20001',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ID またはパスワードが違います。")
        self.assertNotIn('employee_no', self.client.session)

    def test_logout(self):
        self.login_as_employee()
        response = self.client.get(reverse('psys:logout'))
        self.assertRedirects(response, reverse('psys:Index'))
        self.assertNotIn('employee_no', self.client.session)

    def test_login_required_protection(self):
        # 未ログイン時に保護画面へアクセスするとログイン画面へリダイレクトされることを確認
        protected_urls = [
            reverse('psys:MainMenu'),
            reverse('psys:CustomerManagementMenu'),
            reverse('psys:CustomerList'),
            reverse('psys:CustomerSearch'),
            reverse('psys:CustomerRegist'),
            reverse('psys:CustomerDelete'),
            reverse('psys:CustomerUpdate'),
            reverse('psys:OrderSummaryMenu'),
            reverse('psys:MonthlyOrderSummary'),
            reverse('psys:YearlyOrderSummary'),
            reverse('psys:ItemOrderSummary'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(response, reverse('psys:login'), msg_prefix=f"URL {url} should be protected")


class CustomerManagementTests(PsysBaseTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_employee()

    def test_main_menu(self):
        response = self.client.get(reverse('psys:MainMenu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "管理メニュー")
        self.assertContains(response, "得意先管理")
        self.assertContains(response, "得意先集計")

    def test_customer_management_menu(self):
        response = self.client.get(reverse('psys:CustomerManagementMenu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "得意先管理メニュー")
        self.assertContains(response, "得意先一覧")
        self.assertContains(response, "得意先検索")
        self.assertContains(response, "得意先登録")
        self.assertContains(response, "得意先更新")
        self.assertContains(response, "得意先削除")

    def test_customer_list(self):
        response = self.client.get(reverse('psys:CustomerList'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RA0001")
        self.assertContains(response, "A店社")

    def test_customer_search_found(self):
        response = self.client.post(reverse('psys:CustomerSearch'), {
            'seartch_id': 'RA0001'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A店社")
        self.assertContains(response, "06-128-3581")

    def test_customer_search_not_found(self):
        response = self.client.post(reverse('psys:CustomerSearch'), {
            'seartch_id': 'NONEXIST'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "該当する得意先コードは存在しません。")

    def test_customer_regist_page(self):
        response = self.client.get(reverse('psys:CustomerRegist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "得意先登録")
        self.assertContains(response, "RA0016")

    def test_customer_regist_success(self):
        response = self.client.post(reverse('psys:CustomerRegist'), {
            'Customer_name': 'テスト株式会社',
            'Customer_telno': '06-9999-8888',
            'Customer_postalcode': '530-0001',
            'Customer_address': '大阪市北区梅田３丁目',
            'Discount_rate': '5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "登録が完了しました。")
        self.assertTrue(Customer.objects.filter(customer_name='テスト株式会社').exists())

    def test_customer_regist_validation(self):
        response = self.client.post(reverse('psys:CustomerRegist'), {
            'Customer_name': '',  # 未入力
            'Customer_telno': '06-1234-5678',
            'Customer_postalcode': '123-4567',
            'Customer_address': '大阪市',
            'Discount_rate': '0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "登録できませんでした。")
        self.assertContains(response, "得意先名を入力してください。")

    def test_customer_update(self):
        # 検索
        response = self.client.post(reverse('psys:CustomerUpdate'), {
            'action_type': 'search',
            'Customer_code': 'RA0002'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "B店社")

        # 更新
        response = self.client.post(reverse('psys:CustomerUpdate'), {
            'action_type': 'update',
            'Customer_code': 'RA0002',
            'Customer_name': 'B店社（更新後）',
            'Customer_telno': '06-128-3582',
            'Customer_postalcode': '220-0002',
            'Customer_address': '大阪市北区中之島２－２',
            'Discount_rate': '10',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "更新を完了しました。")

        # DB反映確認
        c = Customer.objects.get(customer_code='RA0002')
        self.assertEqual(c.customer_name, 'B店社（更新後）')
        self.assertEqual(c.discount_rate, 10)

    def test_customer_delete_logical(self):
        # 削除前
        self.assertEqual(Customer.objects.filter(customer_code='RA0003', delete_flag=0).count(), 1)

        # 削除リクエスト
        response = self.client.post(reverse('psys:CustomerDelete'), {
            'action_type': 'delete',
            'Customer_code': 'RA0003'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "削除しました。")

        # 論理削除され、有効顧客一覧からは除外されることを確認
        self.assertEqual(Customer.objects.filter(customer_code='RA0003', delete_flag=0).count(), 0)
        c = Customer.objects.get(customer_code='RA0003')
        self.assertEqual(c.delete_flag, 1)


class OrderSummaryTests(PsysBaseTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_employee()

    def test_order_summary_menu(self):
        response = self.client.get(reverse('psys:OrderSummaryMenu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "得意先別集計メニュー")
        self.assertContains(response, "月別受注集計")
        self.assertContains(response, "年次受注集計")
        self.assertContains(response, "商品別受注集計")

    def test_monthly_order_summary(self):
        response = self.client.get(reverse('psys:MonthlyOrderSummary'), {
            'year': '2016',
            'month': '12'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2016年 12月 受注集計結果")
        self.assertContains(response, "RA0001")
        self.assertContains(response, "13,200")
        self.assertContains(response, "RA0015")
        self.assertContains(response, "18,000")
        self.assertContains(response, "31,200")

    def test_yearly_order_summary(self):
        response = self.client.get(reverse('psys:YearlyOrderSummary'), {
            'year': '2016'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2016年 年次受注集計結果")
        self.assertContains(response, "RA0001")
        self.assertContains(response, "14,000")
        self.assertContains(response, "RA0015")
        self.assertContains(response, "18,000")
        self.assertContains(response, "32,000")

    def test_item_order_summary(self):
        response = self.client.get(reverse('psys:ItemOrderSummary'), {
            'customer_code': 'RA0001'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "得意先名")
        self.assertContains(response, "A店社")
        self.assertContains(response, "AR0001")
        self.assertContains(response, "BR0001")
        self.assertContains(response, "CR0001")
        self.assertContains(response, "32,000")


class EmployeeRegistTests(PsysBaseTestCase):
    def test_employee_regist_success(self):
        response = self.client.post(reverse('psys:EmployeeRegist'), {
            'employee_no': 'R20099',
            'employee_name': '新規花子',
            'password': 'pass999'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "新しい従業員が正常に登録されました。")
        self.assertTrue(Employee.objects.filter(employee_no='R20099').exists())

    def test_employee_regist_duplicate(self):
        response = self.client.post(reverse('psys:EmployeeRegist'), {
            'employee_no': 'R20001',  # 既に存在
            'employee_name': '重複一郎',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "既に登録されています")
