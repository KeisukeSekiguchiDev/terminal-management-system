# Terminal Management System (TMS)

カードリーダー端末（TC-200）を一元管理するための端末管理システムです。

## プロジェクト概要

- **目的**: 外部TMSサービス（PayConnect等）の利用料を削減し、自社で端末管理を行う
- **管理対象**: 全顧客のTC-200端末（最大10,000台）
- **開発者**: 1名
- **期間**: 6ヶ月でMVP完成

## システム構成

```
┌─────────────────────┐
│   TMS Server        │
│   (Django/AWS)      │
└──────────┬──────────┘
           │ HTTPS
    ┌──────┴──────┐
    │             │
┌───┴───┐   ┌────┴────┐
│Store A│   │Store B  │
│       │   │         │
│TC-200 │   │TC-200   │
│  ↓USB │   │  ↓USB   │
│Store  │   │Store    │
│  PC   │   │  PC     │
│(Agent)│   │(Agent)  │
└───────┘   └─────────┘
```

## 主な機能

- **端末監視**: リアルタイムでの端末状態監視とアラート通知
- **ファームウェア更新**: OTA（Over-The-Air）による一括更新
- **リモート診断**: 遠隔での端末診断とトラブルシューティング
- **レポート**: 月次レポートと分析機能

## 技術スタック

| コンポーネント | 技術 |
|---------------|------|
| バックエンド | Python / Django |
| データベース | PostgreSQL |
| フロントエンド | Bootstrap 5 |
| インフラ | AWS (EC2, RDS, S3) |
| エージェント | Python (Windows Service) |

## プロジェクト構造

```
Terminal Management System/
├── agent/                    # 店舗PCで動作するエージェント
│   ├── main.py
│   ├── terminal_controller.py
│   └── api_client.py
│
├── server/                   # TMSサーバー (Django)
│   ├── manage.py
│   └── tms_server/
│
├── docs/                     # 日本語ドキュメント
│   ├── 01_project_concept.md
│   ├── 02_as_is_to_be_analysis.md
│   ├── ...
│   └── 14_security_implementation_spec.md
│
└── docs_en/                  # 英語ドキュメント
    ├── 01_project_concept.md
    ├── ...
    └── 14_security_implementation_spec.md
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

## コスト削減効果

| 項目 | PayConnect利用 | 自社開発 | 削減率 |
|------|---------------|----------|--------|
| 月額費用 | ¥100,000/月 | ¥23,000/月 | 77% |
| 年間コスト | ¥1,200,000/年 | ¥276,000/年 | 77% |

**損益分岐点**: 約3年

## マイルストーン

### Phase 1 (1-2ヶ月目)
- [ ] Django環境構築
- [ ] 基本モデル作成
- [ ] 管理画面実装

### Phase 2 (3-4ヶ月目)
- [ ] エージェント開発
- [ ] 監視機能実装
- [ ] アラート機能

### Phase 3 (5-6ヶ月目)
- [ ] ファームウェア更新機能
- [ ] レポート機能
- [ ] 本番環境デプロイ

## ライセンス

MIT License

## 作者

Keisuke Sekiguchi

## 貢献

Issue や Pull Request は歓迎します。
