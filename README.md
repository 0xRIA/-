# 販売支援システム (PSYS) - osu! Cyber Edition

株式会社 健康食品ロイヤル社向け「得意先管理・得意先別集計業務システム」です。  
Django 5.1（Python 3.13）とMySQL 8.3をベースに構築され、ゲーム「osu!」にインスパイアされたスタイリッシュなネオンサイバーデザインを備えています。

---

## 🌟 主な機能

### 1. 共通・認証システム
- **従業員ログイン / ログアウト**: 従業員番号（6桁）とパスワードによる認証、セッション管理
- **アクセス制御ガード**: ログイン必須デコレータ（`@login_required_psys`）による未認証アクセスの自動リダイレクト保護
- **従業員新規登録**: 新規利用従業員のアカウント発行

### 2. 得意先管理サブシステム
- **得意先一覧**: 有効顧客（論理削除除外）の全件表示、詳細・変更・削除へのクイック導線
- **得意先検索**: 得意先コードによるリアルタイム照会、該当なしエラーハンドリング
- **得意先新規登録**: `customer_numbering` テーブルと連携したトランザクション排他ロック（`select_for_update`）による自動採番（`RA0016`〜）
- **得意先変更**: 既存情報の更新
- **得意先削除**: 過去の受注・売上データを安全に保持する**論理削除（`delete_flag = 1`）**

### 3. 得意先別集計サブシステム
- **月別受注集計**: 年・月を指定した得意先別売上合計・総合計（税込）の即時集計
- **年次受注集計**: 年間売上合計および総合計の算出
- **商品別受注集計**: 得意先ごとの商品別受注数量・単価・小計・総合計の集計

---

## 🛠️ 動作要件・技術スタック

- **Python**: 3.13+
- **Django**: 5.1+
- **Database**: MySQL 8.3 (`psysdb3`)
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, osu! Cyber Theme (Outfit / Noto Sans JP)
- **Dependencies**: `mysqlclient`, `sqlparse`, `asgiref`

---

## 🚀 起動手順

### 1. リポジトリのクローン
```powershell
git clone https://github.com/0xRIA/-.git
cd -
```

### 2. 仮想環境の作成と依存関係のインストール
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. データベースセットアップ (MySQL)
MySQLに接続し、データベースの作成と初期SQLを流し込みます：
```sql
CREATE DATABASE psysdb3 CHARACTER SET utf8mb4;
```
```powershell
# 初期データの投入
mysql -u root -p psysdb3 < psysdb.sql
```

> **データベース設定**:  
> `config/settings.py` 内の `DATABASES` 設定をお使いのMySQLユーザー・パスワードに合わせて確認・変更してください。

### 4. サーバーの起動
```powershell
python manage.py runserver
```
起動後、ブラウザで [http://127.0.0.1:8000/](http://127.0.0.1:8000/) にアクセスしてください。

---

## 🧪 テストの実行

全22件の単体・結合テストが実装されています：
```powershell
python manage.py test psys
```

---

## 👤 テスト用アカウント

| 従業員番号 | パスワード | 従業員名 |
|:---:|:---:|:---:|
| `R20001` | `ry000001` | 鈴木一郎 |
| `R20002` | `rx000002` | 山田太郎 |
