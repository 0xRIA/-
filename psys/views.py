from functools import wraps
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from .models import Customer, CustomerNumbering, Employee, Orders, OrderDetails, Item


def login_required_psys(view_func):
    """従業員ログイン必須デコレータ"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('employee_no'):
            messages.warning(request, "この機能を利用するにはログインが必要です。")
            return redirect('psys:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def Index(request):
    """トップページ画面 (Index.html)"""
    return render(request, "psys/Index.html")


def login_view(request):
    """ログイン画面 (Login.html)"""
    if request.method == 'POST':
        employee_no = request.POST.get('Employee_no', '').strip()
        password = request.POST.get('password', '').strip()

        employee = Employee.objects.filter(employee_no=employee_no, password=password).first()
        if employee:
            request.session['employee_no'] = employee.employee_no
            request.session['employee_name'] = employee.employee_name
            messages.success(request, f"ようこそ、{employee.employee_name} さん。")
            return redirect('psys:MainMenu')
        else:
            return render(request, "psys/Login.html", {
                'error': "ID またはパスワードが違います。",
                'employee_no': employee_no
            })
    return render(request, "psys/Login.html")


def logout_view(request):
    """ログアウト処理"""
    request.session.flush()
    messages.info(request, "ログアウトしました。")
    return redirect('psys:Index')


@login_required_psys
def MainMenu(request):
    """管理メニュー画面 (MainMenu.html)"""
    return render(request, "psys/MainMenu.html")


@login_required_psys
def CustomerManagementMenu(request):
    """得意先管理メニュー画面 (CustomerManagementMenu.html)"""
    return render(request, "psys/CustomerManagementMenu.html")


@login_required_psys
def CustomerList(request):
    """得意先一覧画面 (CustomerList.html) - 論理削除されていない得意先を表示"""
    customer_list = Customer.objects.filter(delete_flag=0).order_by('customer_code')
    return render(request, "psys/CustomerList.html", {
        'customer_list': customer_list
    })


@login_required_psys
def CustomerSearch(request):
    """得意先検索画面 (CustomerSearch.html)"""
    customer = None
    error = None
    search_id = None

    if request.method == 'POST':
        search_id = request.POST.get('seartch_id', '').strip()
        if not search_id:
            error = "得意先コードを入力してください。"
        else:
            customer = Customer.objects.filter(customer_code=search_id, delete_flag=0).first()
            if not customer:
                error = "該当する得意先コードは存在しません。"
    else:
        # GETリクエスト（一覧からのリンク等のクエリパラメータ対応）
        search_id = request.GET.get('search_id', '').strip()
        if search_id:
            customer = Customer.objects.filter(customer_code=search_id, delete_flag=0).first()
            if not customer:
                error = "該当する得意先コードは存在しません。"

    return render(request, "psys/CustomerSearch.html", {
        'customer': customer,
        'error': error,
        'seartch_id': search_id
    })


@login_required_psys
def CustomerRegist(request):
    """得意先登録画面 (CustomerRegist.html) - 自動採番およびバリデーション"""
    # 現在の採番情報の取得
    numbering = CustomerNumbering.objects.first()
    current_code = numbering.customer_code if numbering else 15
    next_code = f"RA{current_code + 1:04d}"

    if request.method == 'POST':
        customer_name = request.POST.get('Customer_name', '').strip()
        customer_telno = request.POST.get('Customer_telno', '').strip()
        customer_postalcode = request.POST.get('Customer_postalcode', '').strip()
        customer_address = request.POST.get('Customer_address', '').strip()
        discount_rate_str = request.POST.get('Discount_rate', '0').strip()

        form_errors = []
        if not customer_name:
            form_errors.append("得意先名を入力してください。")
        elif len(customer_name) > 32:
            form_errors.append("得意先名は32文字以内で入力してください。")

        if not customer_telno:
            form_errors.append("電話番号を入力してください。")
        elif len(customer_telno) > 13:
            form_errors.append("電話番号は13文字以内で入力してください。")

        if not customer_postalcode:
            form_errors.append("郵便番号を入力してください。")
        elif len(customer_postalcode) > 8:
            form_errors.append("郵便番号は8文字以内で入力してください。")

        if not customer_address:
            form_errors.append("住所を入力してください。")
        elif len(customer_address) > 40:
            form_errors.append("住所は40文字以内で入力してください。")

        discount_rate = 0
        if discount_rate_str:
            try:
                discount_rate = int(discount_rate_str)
                if discount_rate < 0 or discount_rate > 99:
                    form_errors.append("割引率は0〜99の範囲で入力してください。")
            except ValueError:
                form_errors.append("割引率は半角数値で入力してください。")

        if form_errors:
            return render(request, "psys/CustomerRegist.html", {
                'error_message': "登録できませんでした。",
                'form_errors': form_errors,
                'next_code': next_code,
                'customer_name': customer_name,
                'customer_telno': customer_telno,
                'customer_postalcode': customer_postalcode,
                'customer_address': customer_address,
                'discount_rate': discount_rate_str,
            })

        # 登録処理（トランザクション制御）
        try:
            with transaction.atomic():
                num_record = CustomerNumbering.objects.select_for_update().first()
                if num_record:
                    new_num = num_record.customer_code + 1
                    num_record.customer_code = new_num
                    num_record.save()
                else:
                    new_num = 16
                    CustomerNumbering.objects.create(customer_code=new_num)

                new_customer_code = f"RA{new_num:04d}"
                Customer.objects.create(
                    customer_code=new_customer_code,
                    customer_name=customer_name,
                    customer_telno=customer_telno,
                    customer_postalcode=customer_postalcode,
                    customer_address=customer_address,
                    discount_rate=discount_rate,
                    delete_flag=0
                )

            return render(request, "psys/CustomerRegist.html", {
                'success_message': "登録が完了しました。",
                'registered_code': new_customer_code,
                'next_code': f"RA{new_num + 1:04d}",
            })
        except Exception as e:
            return render(request, "psys/CustomerRegist.html", {
                'error_message': f"登録できませんでした。({str(e)})",
                'next_code': next_code,
            })

    return render(request, "psys/CustomerRegist.html", {
        'next_code': next_code,
    })


@login_required_psys
def CustomerDelete(request):
    """得意先削除画面 (CustomerDelete.html)"""
    customer = None
    error = None
    customer_code = request.GET.get('search_id', '').strip()

    if customer_code:
        customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()
        if not customer:
            error = "該当する得意先コードは存在しません。"

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'search')
        customer_code = request.POST.get('Customer_code', '').strip()

        if action_type == 'search':
            if not customer_code:
                error = "得意先コードを入力してください。"
            else:
                customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()
                if not customer:
                    error = "該当する得意先コードは存在しません。"
            return render(request, "psys/CustomerDelete.html", {
                'customer': customer,
                'error': error,
                'customer_code': customer_code
            })

        elif action_type == 'delete':
            target_customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()
            if target_customer:
                # 論理削除（delete_flag = 1）
                target_customer.delete_flag = 1
                target_customer.save()
                return render(request, "psys/CustomerDeleteResult.html", {
                    'success': True
                })
            else:
                return render(request, "psys/CustomerDeleteResult.html", {
                    'success': False,
                    'error_detail': "（対象の得意先が存在しないか既に削除されています）"
                })

    return render(request, "psys/CustomerDelete.html", {
        'customer': customer,
        'error': error,
        'customer_code': customer_code
    })


@login_required_psys
def CustomerDeleteResult(request):
    """得意先削除結果画面 (CustomerDeleteResult.html)"""
    return render(request, "psys/CustomerDeleteResult.html", {'success': True})


@login_required_psys
def CustomerUpdate(request):
    """得意先更新画面 (CustomerUpdate.html)"""
    customer = None
    error = None
    customer_code = request.GET.get('search_id', '').strip()

    if customer_code:
        customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()
        if not customer:
            error = "該当する得意先コードは存在しません。"

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'search')
        customer_code = request.POST.get('Customer_code', '').strip()

        if action_type == 'search':
            if not customer_code:
                error = "得意先コードを入力してください。"
            else:
                customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()
                if not customer:
                    error = "該当する得意先コードは存在しません。"
            return render(request, "psys/CustomerUpdate.html", {
                'customer': customer,
                'error': error,
                'customer_code': customer_code
            })

        elif action_type == 'update':
            target_customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()
            if not target_customer:
                return render(request, "psys/CustomerUpdateResult.html", {
                    'success': False,
                    'error_detail': "（対象の得意先が見つかりません）"
                })

            customer_name = request.POST.get('Customer_name', '').strip()
            customer_telno = request.POST.get('Customer_telno', '').strip()
            customer_postalcode = request.POST.get('Customer_postalcode', '').strip()
            customer_address = request.POST.get('Customer_address', '').strip()
            discount_rate_str = request.POST.get('Discount_rate', '0').strip()

            try:
                discount_rate = int(discount_rate_str)
            except ValueError:
                discount_rate = 0

            target_customer.customer_name = customer_name
            target_customer.customer_telno = customer_telno
            target_customer.customer_postalcode = customer_postalcode
            target_customer.customer_address = customer_address
            target_customer.discount_rate = discount_rate
            target_customer.save()

            return render(request, "psys/CustomerUpdateResult.html", {
                'success': True
            })

    return render(request, "psys/CustomerUpdate.html", {
        'customer': customer,
        'error': error,
        'customer_code': customer_code
    })


@login_required_psys
def CustomerUpdateResult(request):
    """得意先更新結果画面 (CustomerUpdateResult.html)"""
    return render(request, "psys/CustomerUpdateResult.html", {'success': True})


@login_required_psys
def OrderSummaryMenu(request):
    """得意先別集計メニュー (OrderSummaryMenu.html)"""
    return render(request, "psys/OrderSummaryMenu.html")


@login_required_psys
def MonthlyOrderSummary(request):
    """月別受注集計 (MonthlyOrderSummary.html)"""
    year_str = request.GET.get('year', '').strip()
    month_str = request.GET.get('month', '').strip()

    searched = False
    summary_list = []
    grand_total = 0
    year = None
    month = None

    if year_str and month_str:
        try:
            year = int(year_str)
            month = int(month_str)
            searched = True

            orders_qs = Orders.objects.filter(
                order_date__year=year,
                order_date__month=month
            )
            raw_summary = orders_qs.values(
                'customer_code',
                'customer_code__customer_name'
            ).annotate(
                total_amount=Sum('total_price')
            ).order_by('customer_code')

            for s in raw_summary:
                summary_list.append({
                    'customer_code': s['customer_code'],
                    'customer_name': s['customer_code__customer_name'] or '名称未設定',
                    'total_amount': s['total_amount'] or 0
                })
                grand_total += (s['total_amount'] or 0)
        except ValueError:
            pass

    return render(request, "psys/MonthlyOrderSummary.html", {
        'searched': searched,
        'summary_list': summary_list,
        'grand_total': grand_total,
        'year': year,
        'month': month,
        'default_year': 2016,
        'months': list(range(1, 13))
    })


@login_required_psys
def YearlyOrderSummary(request):
    """年次受注集計 (YearlyOrderSummary.html)"""
    year_str = request.GET.get('year', '').strip()

    searched = False
    summary_list = []
    grand_total = 0
    year = None

    if year_str:
        try:
            year = int(year_str)
            searched = True

            orders_qs = Orders.objects.filter(
                order_date__year=year
            )
            raw_summary = orders_qs.values(
                'customer_code',
                'customer_code__customer_name'
            ).annotate(
                total_amount=Sum('total_price')
            ).order_by('customer_code')

            for s in raw_summary:
                summary_list.append({
                    'customer_code': s['customer_code'],
                    'customer_name': s['customer_code__customer_name'] or '名称未設定',
                    'total_amount': s['total_amount'] or 0
                })
                grand_total += (s['total_amount'] or 0)
        except ValueError:
            pass

    return render(request, "psys/YearlyOrderSummary.html", {
        'searched': searched,
        'summary_list': summary_list,
        'grand_total': grand_total,
        'year': year,
        'default_year': 2016
    })


@login_required_psys
def ItemOrderSummary(request):
    """商品別受注集計 (ItemOrderSummary.html)"""
    customer_code = request.GET.get('customer_code', '').strip()

    searched = False
    customer = None
    item_summary_list = []
    grand_total = 0

    if customer_code:
        searched = True
        customer = Customer.objects.filter(customer_code=customer_code, delete_flag=0).first()

        if customer:
            order_nos = Orders.objects.filter(customer_code=customer_code).values_list('order_no', flat=True)
            details_qs = OrderDetails.objects.filter(order_no__in=order_nos)

            raw_items = details_qs.values(
                'item_code',
                'item_code__item_name',
                'item_code__price'
            ).annotate(
                total_quantity=Sum('order_num'),
                total_amount=Sum('order_price')
            ).order_by('item_code')

            for it in raw_items:
                item_total = it['total_amount'] or 0
                item_summary_list.append({
                    'item_code': it['item_code'],
                    'item_name': it['item_code__item_name'] or '名称未設定',
                    'unit_price': it['item_code__price'] or 0,
                    'total_quantity': it['total_quantity'] or 0,
                    'item_total': item_total
                })
                grand_total += item_total

    return render(request, "psys/ItemOrderSummary.html", {
        'searched': searched,
        'customer': customer,
        'customer_code': customer_code,
        'item_summary_list': item_summary_list,
        'grand_total': grand_total
    })


def EmployeeRegist(request):
    """従業員新規登録画面 (EmployeeRegist.html)"""
    if request.method == 'POST':
        employee_no = request.POST.get('employee_no', '').strip()
        employee_name = request.POST.get('employee_name', '').strip()
        password = request.POST.get('password', '').strip()

        if not employee_no or not employee_name or not password:
            return render(request, "psys/EmployeeRegist.html", {
                'error_message': "すべての項目を入力してください。",
                'employee_no': employee_no,
                'employee_name': employee_name
            })

        if Employee.objects.filter(employee_no=employee_no).exists():
            return render(request, "psys/EmployeeRegist.html", {
                'error_message': f"従業員番号「{employee_no}」は既に登録されています。",
                'employee_no': employee_no,
                'employee_name': employee_name
            })

        Employee.objects.create(
            employee_no=employee_no,
            employee_name=employee_name,
            password=password
        )

        return render(request, "psys/EmployeeRegist.html", {
            'success_message': "新しい従業員が正常に登録されました。",
            'employee_no': employee_no,
            'employee_name': employee_name
        })

    return render(request, "psys/EmployeeRegist.html")