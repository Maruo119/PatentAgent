# PatentAgent - 特許情報自動取得・Slack通知システム

特許庁公式APIを利用して、保険関連の特許情報を定期的に取得し、Slackで通知するシステムです。AWS Lambda + EventBridgeで毎日20:00に自動実行されます。

## 機能

- 🔍 特許庁公式APIを利用した特許情報の自動取得
- 📋 CSVで管理される検索キーワード（保険、損保、生保など）
- 💬 Slack Webhookでの自動通知
- ⏰ 毎日20:00の定期実行（AWS EventBridge）
- 🔄 重複排除機能（同一特許の重複通知を防止）

## プロジェクト構成

```
PatentAgent/
├── src/
│   ├── lambda/
│   │   ├── handler.py          # Lambda エントリーポイント
│   │   ├── patent_api.py       # 特許庁API操作
│   │   ├── slack_notifier.py   # Slack通知
│   │   └── utils.py            # ユーティリティ
│   └── config/
│       └── keywords.csv        # 検索キーワード設定
├── doc/
│   ├── architecture.md         # システムアーキテクチャ
│   ├── setup.md               # AWS セットアップ手順
│   └── api_reference.md       # API参考情報
├── .env.example               # 環境変数テンプレート
├── requirements.txt           # Python依存パッケージ
└── README.md                  # このファイル
```

## セットアップ

### ローカル検証（フェーズ1）

1. **リポジトリクローン**

```bash
git clone https://github.com/your-org/PatentAgent.git
cd PatentAgent
```

2. **環境変数設定**

`.env.example` をコピーして `.env` を作成：

```bash
cp .env.example .env
```

`.env` に以下を記入（API認証情報は別途提供されるもの）：

```
JPO_API_ID=YOUR_API_ID
JPO_API_PASSWORD=YOUR_API_PASSWORD
JPO_TOKEN_URL=https://ip-data.jpo.go.jp/auth/token
SLACK_WEBHOOK_URL=YOUR_WEBHOOK_URL
```

API認証情報（JPO_API_ID、JPO_API_PASSWORD）は、[特許庁APIサイト](https://ip-data.jpo.go.jp/pages/top.html)から取得してください。

3. **Python依存パッケージインストール**

```bash
pip install -r requirements.txt
```

4. **検索キーワード設定**

`src/config/keywords.csv` を編集して検索キーワードを追加：

```csv
keyword,category
保険,insurance
損保,insurance
生保,insurance
```

5. **ローカルテスト**

```bash
# ハンドラーのテスト実行
python -c "
import sys
sys.path.insert(0, 'src/lambda')
from handler import lambda_handler
result = lambda_handler({}, None)
print(result)
"
```

### AWS デプロイ（フェーズ2以降）

詳細なAWS セットアップ手順は [doc/setup.md](doc/setup.md) を参照してください。

**概要：**

1. IAM ロール作成（Lambda実行ロール）
2. EventBridge ルール作成（cron: `0 20 * * ? *`）
3. Lambda 関数デプロイ
4. 環境変数設定
5. S3 バケット作成・keywords.csv 格納
6. AWS Secrets Manager でシークレット管理（フェーズ2）

## 検索キーワードの管理

`src/config/keywords.csv` を編集することで、検索キーワードを追加・変更できます：

```csv
keyword,category
保険,insurance
損害保険,insurance
生命保険,insurance
医療保険,insurance
火災保険,insurance
```

- **keyword**: 特許庁APIで検索するキーワード
- **category**: キーワードのカテゴリー（ユーザー参考用）

## Slack通知形式

毎日20:00に以下のようなメッセージが Slack に送信されます：

```
特許情報取得レポート
実行日時: 2026-05-31 20:00:00
合計件数: 15件

キーワード: 保険
件数: 8件
• 保険商品の販売方法
  特許番号: JP2026000001
  出願人: 株式会社ABC
  公開日: 2026-05-30
...

キーワード: 損保
件数: 7件
...
```

## トラブルシューティング

### API認証エラー

- JPO_API_ID、JPO_API_PASSWORD を確認
- API提供サイト: https://ip-data.jpo.go.jp/pages/top.html

### Slack通知が送信されない

- SLACK_WEBHOOK_URL の形式確認
- Slack ワークスペースの Webhook設定確認

### キーワードが読み込まれない

- `src/config/keywords.csv` が UTF-8 エンコーディングか確認
- CSV 形式が正しいか確認（headers: keyword, category）

## ドキュメント

- [システムアーキテクチャ](doc/architecture.md)
- [AWS セットアップ手順](doc/setup.md)
- [API参考情報](doc/api_reference.md)

## ライセンス

MIT

## 作成者

PatentAgent Team
