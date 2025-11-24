@echo off
echo ========================================
echo TMS Server セットアップ
echo ========================================

echo.
echo Step 1: 必要なパッケージをインストール
pip install django==4.2 djangorestframework==3.14 python-decouple

echo.
echo Step 2: Djangoプロジェクトを作成
django-admin startproject tms_server .

echo.
echo Step 3: terminalsアプリを作成
python manage.py startapp terminals

echo.
echo Step 4: データベース初期化
python manage.py makemigrations
python manage.py migrate

echo.
echo Step 5: 管理者ユーザー作成
echo ユーザー名: admin
echo パスワード: 自分で決めてください
python manage.py createsuperuser

echo.
echo ========================================
echo セットアップ完了！
echo.
echo 次の手順:
echo 1. python manage.py runserver
echo 2. ブラウザで http://localhost:8000/admin を開く
echo ========================================
pause