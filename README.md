# Terminal Management System (TMS)

カードリーダー端末（TC-200）を一元管理するための端末管理システムです。

## プロジェクト概要

- **目的**: 外部TMSサービス（PayConnect等）の利用料を削減し、自社で端末管理を行う
- **管理対象**: 全顧客のTC-200端末（最大10,000台）
- **開発者**: 1名
- **期間**: 6ヶ月でMVP完成
- **実装状況**: MVP機能実装完了（80%準拠）

## システム構成

```
┌─────────────────────────────────────────────┐
│         TechCore Solutions 本社              │
│                                             │
│  ┌──────────────┐    ┌──────────────┐      │
│  │ TMS Admin    │    │  サポート     │      │
│  │  (Django)    │<-->│   チーム      │      │
│  └──────────────┘    └──────────────┘      │
│         |                                   │
└─────────|───────────────────────────────────┘
          | HTTPS (AWS)
          |
    ┌─────┴─────────────────────┐
    |                           |
┌───┴────┐  ┌────┴────┐  ┌────┴────┐
│顧客 A  │  │顧客 B   │  │顧客 C   │
│        │  │         │  │         │
│TC-200  │  │TC-200   │  │TC-200   │
│↓USB    │  │↓USB     │  │↓USB     │
│店舗PC  │  │店舗PC   │  │店舗PC   │
│(Agent) │  │(Agent)  │  │(Agent)  │
└────────┘  └─────────┘  └─────────┘
```

## 実装済み機能

### サーバー (Django REST Framework)
- **認証**: JWT認証（SimpleJWT）、MFA対応
- **端末管理**: CRUD操作、状態監視、コマンド送信
- **顧客管理**: 顧客情報、契約管理
- **アラート管理**: 重要度別アラート、確認/解決フロー
- **ファームウェア管理**: バージョン管理、一括デプロイ
- **レポート**: 稼働率、アラート統計

### Web UI (Bootstrap 5)
- ダッシュボード（KPI表示、稼働率グラフ）
- 端末一覧/詳細（フィルタ、検索、ページネーション）
- 顧客一覧/詳細
- アラート一覧（重要度/状態フィルタ）
- ファームウェア管理（アップロード、デプロイ）
- レポート画面（グラフ、統計）

### エージェント (Windows)
- ハートビート送信（5分間隔）
- 端末状態監視（CPU、メモリ、ディスク）
- コマンド受信/実行（再起動、ファームウェア更新）
- TC-200 DLL連携（モックモード対応）

## 技術スタック

| コンポーネント | 技術 | バージョン |
|---------------|------|-----------|
| バックエンド | Python / Django | 4.2 |
| API | Django REST Framework | 3.14 |
| 認証 | SimpleJWT | 5.3 |
| データベース | PostgreSQL | 13+ |
| キャッシュ | Redis | 5.0 |
| タスクキュー | Celery | 5.3 |
| フロントエンド | Bootstrap | 5.3 |
| インフラ | AWS (EC2, RDS, S3) | - |
| エージェント | Python (Windows Service) | 3.9+ |

## プロジェクト構造

```
Terminal Management System/
├── agent/                    # 店舗PCで動作するエージェント
│   ├── main.py              # メインエージェントクラス
│   ├── terminal_controller.py # TC-200端末制御
│   ├── api_client.py        # サーバーAPI通信
│   ├── config.py            # 設定管理
│   └── monitoring.py        # システム監視
│
├── server/                   # TMSサーバー (Django)
│   ├── manage.py
│   ├── tms_server/          # プロジェクト設定
│   │   ├── settings.py
│   │   └── urls.py
│   └── terminals/           # メインアプリ
│       ├── models.py        # データベースモデル
│       ├── views.py         # REST APIビュー
│       ├── web_views.py     # Web UIビュー
│       ├── serializers.py   # APIシリアライザ
│       ├── admin.py         # 管理画面設定
│       ├── templates/       # HTMLテンプレート
│       └── tests/           # テストコード
│
├── docs/                     # 日本語ドキュメント
│   └── (14ファイル)
│
├── docs_en/                  # 英語ドキュメント
│   └── (14ファイル)
│
├── requirements.txt          # Python依存パッケージ
└── README.md
```

## ドキュメント

### 日本語 (docs/)

| ファイル | 内容 |
|---------|------|
| 01_project_concept.md | 事業・システム構想 |
| 02_as_is_to_be_analysis.md | As-Is/To-Be業務分析 |
| 03_development_strategy.md | 開発戦略 |
| 04_functional_requirements.md | 機能要件定義 |
| 05_quick_start_guide.md | クイックスタートガイド |
| 06_business_model_analysis.md | ビジネスモデル分析 |
| 07_system_architecture_final.md | システムアーキテクチャ設計 |
| 08_database_design_detail.md | データベース詳細設計 |
| 09_api_specification.md | API仕様書 |
| 10_screen_specification.md | 画面仕様書 |
| 11_test_specification.md | テスト仕様書 |
| 12_deployment_guide.md | デプロイメント手順書 |
| 13_agent_implementation_spec.md | エージェント実装仕様書 |
| 14_security_implementation_spec.md | セキュリティ実装仕様書 |

### English (docs_en/)

Same documents translated to English for international development teams.

## 開発環境のセットアップ

### 前提条件

- Python 3.9+
- PostgreSQL 13+
- Node.js 14+ (フロントエンドビルド用)

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/KeisukeSekiguchiDev/terminal-management-system.git
cd terminal-management-system

# Python仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt

# データベースのセットアップ
cd server
python manage.py migrate
python manage.py createsuperuser

# 開発サーバーの起動
python manage.py runserver
```

## 実装状況

### Phase 1: 基盤構築 - 完了
- [x] Django環境構築
- [x] 基本モデル作成（8テーブル）
- [x] 管理画面実装
- [x] JWT認証実装

### Phase 2: REST API - 完了
- [x] 認証API（ログイン、トークン更新）
- [x] 端末API（CRUD、コマンド送信）
- [x] 顧客API（CRUD）
- [x] アラートAPI（一覧、確認、解決）
- [x] ファームウェアAPI（アップロード、デプロイ）
- [x] レポートAPI（サマリー、稼働率）
- [x] エージェントAPI（登録、ハートビート、ログ）

### Phase 3: Web UI - 完了
- [x] ログイン画面
- [x] ダッシュボード
- [x] 端末一覧/詳細
- [x] 顧客一覧/詳細
- [x] アラート一覧
- [x] ファームウェア管理
- [x] レポート画面
- [ ] ユーザー管理画面
- [ ] 設定画面

### Phase 4: エージェント - 完了
- [x] ハートビートループ
- [x] 端末監視ループ
- [x] コマンド処理（再起動、ファームウェア更新）
- [x] TC-200 DLL連携
- [ ] 自動更新機能
- [ ] ログ収集コマンド

### Phase 5: セキュリティ・テスト - 完了
- [x] 監査ログミドルウェア
- [x] 単体テスト
- [x] APIテスト

## API エンドポイント

| カテゴリ | エンドポイント | 説明 |
|----------|---------------|------|
| 認証 | POST /api/v1/auth/login | ログイン |
| 認証 | POST /api/v1/auth/refresh | トークン更新 |
| 端末 | GET /api/v1/terminals | 端末一覧 |
| 端末 | GET /api/v1/terminals/{id} | 端末詳細 |
| 端末 | POST /api/v1/terminals/{id}/commands | コマンド送信 |
| 顧客 | GET /api/v1/customers | 顧客一覧 |
| アラート | GET /api/v1/alerts | アラート一覧 |
| アラート | PATCH /api/v1/alerts/{id} | アラート更新 |
| ファームウェア | POST /api/v1/firmware/{id}/deploy | デプロイ |
| レポート | GET /api/v1/reports/summary | サマリー |
| エージェント | POST /api/v1/agent/register | 登録 |
| エージェント | POST /api/v1/agent/heartbeat | ハートビート |

## コスト削減効果

| 項目 | PayConnect利用 | 自社開発 | 削減率 |
|------|---------------|----------|--------|
| 月額費用 | ¥100,000/月 | ¥23,000/月 | 77% |
| 年間コスト | ¥1,200,000/年 | ¥276,000/年 | 77% |

**損益分岐点**: 約3年

## テスト実行

```bash
cd server

# 単体テスト
python manage.py test terminals.tests.test_models

# APIテスト
python manage.py test terminals.tests.test_api

# 全テスト
python manage.py test
```

## ライセンス

MIT License

## 作者

Keisuke Sekiguchi

## 貢献

Issue や Pull Request は歓迎します。
