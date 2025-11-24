# Web開発技術ガイド（初心者向け）
## TMSプロジェクトで使用している技術の解説

**対象読者**: Webアプリケーション開発の経験がない方
**目的**: このプロジェクトで使用している技術がどのように連携して動作しているかを理解する

---

## 目次

1. [Webアプリケーションの基本概念](#1-webアプリケーションの基本概念)
2. [技術スタック全体像](#2-技術スタック全体像)
3. [各技術の役割と関係](#3-各技術の役割と関係)
4. [データの流れ](#4-データの流れ)
5. [実際のコード例](#5-実際のコード例)
6. [用語集](#6-用語集)

---

## 1. Webアプリケーションの基本概念

### 1.1 Webアプリケーションとは？

Webアプリケーションは、**ブラウザ（Chrome、Edge等）を通じて使うソフトウェア**です。

従来のソフトウェア（Word、Excelなど）との違い：
- インストール不要（ブラウザがあれば使える）
- どのPCからでもアクセス可能
- データはサーバーに保存される

### 1.2 クライアントとサーバー

```
┌─────────────┐                    ┌─────────────┐
│  クライアント  │  ←─ インターネット ─→  │   サーバー   │
│  (ブラウザ)   │                    │  (Django)   │
└─────────────┘                    └─────────────┘
    あなたのPC                         AWS上のPC
```

- **クライアント**: ユーザーが操作する側（ブラウザ）
- **サーバー**: データを管理し、処理を行う側（Django）

### 1.3 リクエストとレスポンス

Webアプリケーションは「お願い」と「返答」の繰り返しで動きます。

```
1. ユーザーがURLにアクセス → リクエスト（お願い）
2. サーバーがデータを処理 → 処理
3. サーバーが結果を返す → レスポンス（返答）
4. ブラウザが画面を表示 → 表示
```

**例**: 端末一覧を見たいとき
```
1. ブラウザで /terminals にアクセス（リクエスト）
2. Djangoがデータベースから端末データを取得（処理）
3. HTML形式でデータを返す（レスポンス）
4. ブラウザが表を表示（表示）
```

---

## 2. 技術スタック全体像

### 2.1 技術の役割マップ

```
┌─────────────────────────────────────────────────────────┐
│                    ユーザーのブラウザ                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  HTML (構造) + CSS (見た目) + JavaScript (動き)  │   │
│  │              Bootstrap 5 (デザイン補助)           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↑↓ HTTP/HTTPS通信
┌─────────────────────────────────────────────────────────┐
│                      サーバー (AWS)                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Django (Webフレームワーク)                       │   │
│  │    ├─ URL処理 (どのページを表示するか)            │   │
│  │    ├─ ビュー (処理ロジック)                       │   │
│  │    ├─ モデル (データ構造定義)                     │   │
│  │    └─ テンプレート (HTML生成)                     │   │
│  │                                                   │   │
│  │  Django REST Framework (API提供)                  │   │
│  │    └─ JSON形式でデータを送受信                    │   │
│  └─────────────────────────────────────────────────┘   │
│                          ↑↓                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ PostgreSQL  │  │   Redis     │  │   Celery    │   │
│  │ (データベース) │  │ (キャッシュ)  │  │ (非同期処理) │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 料理に例えると

| 技術 | 料理での役割 | 説明 |
|------|-------------|------|
| **Django** | シェフ | リクエストを受けて、適切な処理をして結果を返す |
| **PostgreSQL** | 冷蔵庫 | 材料（データ）を保存・取り出しする |
| **Redis** | カウンター | よく使う材料を手元に置いておく（高速アクセス） |
| **Celery** | 助手 | 時間のかかる作業を別で進める |
| **Bootstrap** | 盛り付けセット | 見栄えの良い皿や飾りを提供 |
| **HTML/CSS/JS** | 料理の見た目 | 最終的にお客さんに出す形 |

---

## 3. 各技術の役割と関係

### 3.1 Python

**役割**: プログラミング言語（サーバー側の処理を書く）

```python
# Pythonのコード例
def calculate_total(prices):
    total = 0
    for price in prices:
        total = total + price
    return total

result = calculate_total([100, 200, 300])
print(result)  # 600
```

**特徴**:
- 読みやすい文法
- 豊富なライブラリ
- Web開発からAIまで幅広く使用

### 3.2 Django（ジャンゴ）

**役割**: Webアプリケーションフレームワーク

「フレームワーク」とは、**よく使う機能があらかじめ用意されたツールセット**です。

**Djangoが提供する機能**:
- URLとページの紐付け
- データベース操作の簡略化
- ユーザー認証
- セキュリティ対策
- 管理画面の自動生成

**なぜDjangoを使うのか？**
```
ゼロから作る場合:
- ユーザー認証を自分で実装 → 数週間
- データベース接続を自分で実装 → 数日
- セキュリティ対策を自分で実装 → 数週間

Djangoを使う場合:
- 全て用意されている → すぐに使える
```

### 3.3 Django REST Framework（DRF）

**役割**: APIを簡単に作るためのツール

**APIとは？**
アプリケーション同士がデータをやり取りするための窓口です。

```
通常のWebページ:
  サーバー → HTML（人間が見る用）→ ブラウザ

API:
  サーバー → JSON（プログラムが読む用）→ アプリ/他のシステム
```

**JSONの例**:
```json
{
  "terminal_id": 1,
  "serial_number": "TC200-001",
  "status": "online",
  "customer": "ABC商店"
}
```

**TMSでの使われ方**:
- Web画面 → 通常のDjangoで表示
- エージェント → APIでデータ送受信

### 3.4 PostgreSQL（ポストグレスキューエル）

**役割**: データベース（データを永続的に保存）

**データベースとは？**
データを整理して保存する仕組みです。Excelの表のようなイメージ。

**terminalsテーブルの例**:
| id | serial_number | status | customer_id | last_heartbeat |
|----|--------------|--------|-------------|----------------|
| 1 | TC200-001 | online | 1 | 2025-11-24 10:00 |
| 2 | TC200-002 | offline | 1 | 2025-11-24 09:30 |
| 3 | TC200-003 | error | 2 | 2025-11-24 09:45 |

**SQL（データベース言語）の例**:
```sql
-- オンラインの端末を取得
SELECT * FROM terminals WHERE status = 'online';

-- 新しい端末を追加
INSERT INTO terminals (serial_number, status)
VALUES ('TC200-004', 'online');
```

**DjangoではSQLを書かなくてよい**:
```python
# Djangoでの書き方（Python）
online_terminals = Terminal.objects.filter(status='online')
```

### 3.5 Redis（レディス）

**役割**: キャッシュ（よく使うデータを一時保存）

**なぜ必要？**

データベースへのアクセスは時間がかかります。
頻繁にアクセスするデータはRedisに保存して高速化します。

```
データベースから取得: 100ミリ秒
Redisから取得:       1ミリ秒
```

**TMSでの使用例**:
- ダッシュボードの統計情報
- ログイン中のユーザー情報（セッション）

### 3.6 Celery（セロリ）

**役割**: 非同期タスク処理（時間のかかる処理を別で実行）

**問題点**:
```
ファームウェア更新を1000台に配信する場合:
→ 1台3秒 × 1000台 = 3000秒（50分）
→ ユーザーは50分待つことに...
```

**Celeryでの解決**:
```
1. ユーザーが「更新開始」をクリック
2. サーバーは「受け付けました」とすぐに返答
3. Celeryが裏で1000台に配信を実行
4. ユーザーは他の作業ができる
5. 完了したら通知
```

### 3.7 Bootstrap（ブートストラップ）

**役割**: CSSフレームワーク（見た目を簡単に整える）

**CSSを一から書く場合**:
```css
.button {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}
.button:hover {
  background-color: #0056b3;
}
```

**Bootstrapを使う場合**:
```html
<button class="btn btn-primary">ボタン</button>
```

これだけで青いボタンが作れます。

**Bootstrapの提供する部品**:
- ボタン、フォーム、テーブル
- ナビゲーションバー
- カード、モーダル（ポップアップ）
- グリッドシステム（レイアウト）
- レスポンシブデザイン（スマホ対応）

### 3.8 AWS（アマゾン ウェブ サービス）

**役割**: クラウドインフラ（サーバーを借りる）

**自社でサーバーを持つ場合**:
- サーバー機器の購入（数十万円）
- 設置場所の確保
- 電気代、冷却費用
- 故障時の対応
- セキュリティ対策

**AWSを使う場合**:
- 必要な分だけ借りる（従量課金）
- すぐに使い始められる
- スケールアップ/ダウンが簡単
- Amazonが管理

**TMSで使用するAWSサービス**:
| サービス | 役割 |
|---------|------|
| EC2 | サーバー（Djangoが動く） |
| RDS | データベース（PostgreSQL） |
| S3 | ファイル保存（ファームウェア等） |
| CloudWatch | 監視・ログ |

---

## 4. データの流れ

### 4.1 端末一覧を表示する流れ

```
ユーザー                    サーバー                   データベース
   │                          │                          │
   │ 1. /terminals にアクセス   │                          │
   │ ────────────────────────→ │                          │
   │                          │ 2. 端末データを要求         │
   │                          │ ─────────────────────────→ │
   │                          │                          │
   │                          │ 3. 端末データを返す         │
   │                          │ ←───────────────────────── │
   │                          │                          │
   │ 4. HTMLページを返す        │                          │
   │ ←──────────────────────── │                          │
   │                          │                          │
   ▼                          │                          │
 画面表示                       │                          │
```

### 4.2 端末がハートビートを送る流れ

```
エージェント                  サーバー                   データベース
   │                          │                          │
   │ 1. POST /api/v1/agent/heartbeat                      │
   │    {serial: "TC200-001", cpu: 45, memory: 60}        │
   │ ────────────────────────→ │                          │
   │                          │ 2. 端末データを更新         │
   │                          │ ─────────────────────────→ │
   │                          │                          │
   │                          │ 3. 更新完了                │
   │                          │ ←───────────────────────── │
   │                          │                          │
   │ 4. {status: "ok", commands: [...]}                   │
   │ ←──────────────────────── │                          │
   │                          │                          │
   ▼                          │                          │
コマンドがあれば実行              │                          │
```

### 4.3 ファームウェア一括更新の流れ

```
ユーザー        サーバー        Celery         データベース
   │              │              │                │
   │ 1. 更新開始   │              │                │
   │ ───────────→ │              │                │
   │              │ 2. タスク登録  │                │
   │              │ ────────────→ │                │
   │              │              │                │
   │ 3. 受付完了   │              │                │
   │ ←─────────── │              │                │
   │              │              │ 4. 端末リスト取得 │
   │ (すぐに      │              │ ──────────────→ │
   │  別の作業へ)  │              │                │
   │              │              │ 5. 各端末に配信  │
   │              │              │ ←────────────── │
   │              │              │                │
   │              │ 6. 完了通知   │                │
   │ ←─────────── ← ───────────── │                │
```

---

## 5. 実際のコード例

### 5.1 モデル（データベース設計）

`server/terminals/models.py` より

```python
from django.db import models

class Terminal(models.Model):
    """端末マスタ"""

    # フィールド定義
    serial_number = models.CharField(
        max_length=50,
        unique=True,              # 重複不可
        verbose_name='シリアル番号'
    )

    customer = models.ForeignKey(
        'Customer',               # Customerテーブルを参照
        on_delete=models.CASCADE, # 顧客削除時に端末も削除
        related_name='terminals'
    )

    status = models.CharField(
        max_length=20,
        choices=[                 # 選択肢を制限
            ('online', 'オンライン'),
            ('offline', 'オフライン'),
            ('error', 'エラー'),
        ],
        default='offline'
    )

    last_heartbeat = models.DateTimeField(
        null=True,                # NULL許可
        blank=True
    )

    # 自動で作成日時を記録
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**解説**:
- `CharField`: 文字列を保存
- `ForeignKey`: 他のテーブルへの参照（リレーション）
- `DateTimeField`: 日時を保存
- `choices`: 選択肢を限定

### 5.2 ビュー（処理ロジック）

`server/terminals/web_views.py` より

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Terminal, Customer

@login_required  # ログイン必須
def terminal_list_view(request):
    """端末一覧画面"""

    # 全端末を取得
    terminals = Terminal.objects.select_related('customer').all()

    # 検索フィルタ
    search = request.GET.get('search')  # URLパラメータを取得
    if search:
        terminals = terminals.filter(
            serial_number__icontains=search  # 部分一致検索
        )

    # ステータスフィルタ
    status = request.GET.get('status')
    if status:
        terminals = terminals.filter(status=status)

    # テンプレートにデータを渡す
    context = {
        'terminals': terminals,
        'customers': Customer.objects.all(),
    }

    return render(request, 'terminals/terminal_list.html', context)
```

**解説**:
- `@login_required`: ログインしていないとアクセス不可
- `request.GET.get()`: URLの`?search=xxx`を取得
- `filter()`: 条件に合うデータを絞り込む
- `render()`: HTMLテンプレートを返す

### 5.3 テンプレート（HTML生成）

`server/terminals/templates/terminals/terminal_list.html` より（簡略化）

```html
{% extends 'base.html' %}  <!-- 共通レイアウトを継承 -->

{% block content %}
<div class="container">
    <h1>端末一覧</h1>

    <!-- 検索フォーム -->
    <form method="get" class="mb-3">
        <input type="text" name="search"
               value="{{ request.GET.search }}"
               placeholder="シリアル番号で検索">
        <button type="submit" class="btn btn-primary">検索</button>
    </form>

    <!-- 端末テーブル -->
    <table class="table">
        <thead>
            <tr>
                <th>シリアル番号</th>
                <th>顧客</th>
                <th>ステータス</th>
            </tr>
        </thead>
        <tbody>
            {% for terminal in terminals %}
            <tr>
                <td>{{ terminal.serial_number }}</td>
                <td>{{ terminal.customer.company_name }}</td>
                <td>
                    {% if terminal.status == 'online' %}
                        <span class="badge bg-success">オンライン</span>
                    {% elif terminal.status == 'offline' %}
                        <span class="badge bg-secondary">オフライン</span>
                    {% else %}
                        <span class="badge bg-danger">エラー</span>
                    {% endif %}
                </td>
            </tr>
            {% empty %}
            <tr>
                <td colspan="3">端末がありません</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

**解説**:
- `{% extends %}`: 共通レイアウトを継承
- `{% for ... %}`: ループ処理
- `{{ variable }}`: 変数を表示
- `{% if ... %}`: 条件分岐
- `class="btn btn-primary"`: Bootstrapのクラス

### 5.4 API（REST API）

`server/terminals/views.py` より

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class TerminalListView(APIView):
    """端末一覧API"""

    permission_classes = [IsAuthenticated]  # 認証必須

    def get(self, request):
        """GET /api/v1/terminals"""

        terminals = Terminal.objects.all()

        # フィルタリング
        status = request.query_params.get('status')
        if status:
            terminals = terminals.filter(status=status)

        # シリアライズ（Python→JSON変換）
        serializer = TerminalListSerializer(terminals, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })
```

**レスポンス例**:
```json
{
    "status": "success",
    "data": [
        {
            "id": 1,
            "serial_number": "TC200-001",
            "status": "online",
            "customer_name": "ABC商店"
        },
        {
            "id": 2,
            "serial_number": "TC200-002",
            "status": "offline",
            "customer_name": "ABC商店"
        }
    ]
}
```

### 5.5 エージェント（API通信）

`agent/api_client.py` より

```python
import requests

class APIClient:
    """サーバーとの通信を担当"""

    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    def send_heartbeat(self, serial_number, metrics):
        """ハートビートを送信"""

        url = f"{self.base_url}/api/v1/agent/heartbeat"

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        data = {
            'serial_number': serial_number,
            'cpu_usage': metrics['cpu'],
            'memory_usage': metrics['memory'],
            'disk_usage': metrics['disk']
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code}")
```

**解説**:
- `requests`: HTTPリクエストを送るライブラリ
- `Bearer {token}`: JWT認証トークンをヘッダーに付与
- `response.json()`: JSONレスポンスをPython辞書に変換

---

## 6. 用語集

### A-E

| 用語 | 読み方 | 説明 |
|------|--------|------|
| **API** | エーピーアイ | アプリケーション間でデータをやり取りする窓口 |
| **AWS** | エーダブリューエス | Amazonが提供するクラウドサービス |
| **Bootstrap** | ブートストラップ | 見た目を簡単に整えるCSSフレームワーク |
| **Celery** | セロリ | 非同期タスク処理ライブラリ |
| **CRUD** | クラッド | Create, Read, Update, Delete の略。基本操作 |
| **CSS** | シーエスエス | Webページの見た目を定義する言語 |
| **Django** | ジャンゴ | PythonのWebフレームワーク |

### F-J

| 用語 | 読み方 | 説明 |
|------|--------|------|
| **Framework** | フレームワーク | よく使う機能が用意されたツールセット |
| **HTML** | エイチティーエムエル | Webページの構造を定義する言語 |
| **HTTP/HTTPS** | エイチティーティーピー | Webでデータを送受信する通信規約 |
| **JavaScript** | ジャバスクリプト | Webページに動きをつける言語 |
| **JSON** | ジェイソン | データ交換用のテキスト形式 |
| **JWT** | ジェイダブリューティー | トークンベースの認証方式 |

### K-P

| 用語 | 読み方 | 説明 |
|------|--------|------|
| **Model** | モデル | データベースのテーブル定義 |
| **ORM** | オーアールエム | SQLを書かずにDBを操作する仕組み |
| **PostgreSQL** | ポストグレスキューエル | オープンソースのデータベース |
| **Python** | パイソン | プログラミング言語 |

### Q-Z

| 用語 | 読み方 | 説明 |
|------|--------|------|
| **Redis** | レディス | 高速なキャッシュ/データストア |
| **REST API** | レスト エーピーアイ | HTTPを使ったAPIの設計スタイル |
| **SQL** | エスキューエル | データベースを操作する言語 |
| **Template** | テンプレート | HTMLを動的に生成する仕組み |
| **URL** | ユーアールエル | Webページのアドレス |
| **View** | ビュー | リクエストを処理するロジック |

---

## まとめ

### このプロジェクトの技術構成

```
[ユーザー]
    ↓ ブラウザでアクセス
[Bootstrap + HTML/CSS/JS] - 見た目
    ↓
[Django] - 処理の司令塔
    ├─ [Django REST Framework] - API提供
    ├─ [PostgreSQL] - データ保存
    ├─ [Redis] - 高速キャッシュ
    └─ [Celery] - 非同期処理

[AWS] - 全体を動かすインフラ
```

### 学習の進め方

1. **まずPythonの基礎**
   - 変数、関数、クラス
   - ファイル操作

2. **次にDjangoのチュートリアル**
   - 公式チュートリアル（日本語あり）
   - 簡単なブログアプリを作る

3. **データベースの基礎**
   - SQLの基本（SELECT, INSERT, UPDATE, DELETE）
   - Djangoでのモデル定義

4. **REST APIの理解**
   - HTTPメソッド（GET, POST, PUT, DELETE）
   - JSONの読み書き

5. **実際のコードを読む**
   - このプロジェクトのコードを読んで理解

### おすすめ学習リソース

- **Python**: [Python公式チュートリアル](https://docs.python.org/ja/3/tutorial/)
- **Django**: [Django Girls Tutorial](https://tutorial.djangogirls.org/ja/)
- **SQL**: [SQLZOO](https://sqlzoo.net/)
- **Web基礎**: [MDN Web Docs](https://developer.mozilla.org/ja/)

---

**作成日**: 2025年11月24日
**対象プロジェクト**: Terminal Management System (TMS)
