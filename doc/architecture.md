# システムアーキテクチャ詳細

## システム概要

PatentAgent は、特許庁公式API（Japan Patent Office Data API）を利用して、保険関連の特許情報を定期的に取得し、Slack経由でユーザーに通知する自動化システムです。AWS Lambda + EventBridge を利用することで、スケーラブルかつ費用効率的なソリューションを実現します。

## アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS クラウド環境                          │
│                                                               │
│  ┌──────────────┐                                            │
│  │ EventBridge  │                                            │
│  │ (毎日20:00)  │                                            │
│  └────────┬─────┘                                            │
│           │ cron(0 20 * * ? *)                              │
│           ▼                                                  │
│  ┌────────────────────────────────────────┐                │
│  │        AWS Lambda Function             │                │
│  │  ┌─────────────────────────────────┐   │                │
│  │  │ handler.py (Lambda Handler)     │   │                │
│  │  │ - フロー制御                     │   │                │
│  │  │ - エラーハンドリング             │   │                │
│  │  └──┬──────────────┬────────────┬──┘   │                │
│  │     │              │            │       │                │
│  │     ▼              ▼            ▼       │                │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┤                │
│  │  │keywords │  │patent_api│  │slack_   │                │
│  │  │(読込)   │  │(検索)    │  │notifier │                │
│  │  │         │  │          │  │(通知)   │                │
│  │  └─────────┘  └──────────┘  └──────────┤                │
│  │                                         │                │
│  └─────────────────────────────────────────┘                │
│           │                        │                        │
│           │                        │                        │
│           ▼                        ▼                        │
│  ┌──────────────────┐    ┌────────────────────────┐        │
│  │ S3 Bucket        │    │ Environment Variables  │        │
│  │ keywords.csv     │    │ (API Credentials)      │        │
│  │ (設定ファイル)    │    │ (Secrets Manager)      │        │
│  └──────────────────┘    └────────────────────────┘        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                                  │
         └──────────────┬───────────────────┘
                        │
         ┌──────────────┴───────────────────┐
         │                                  │
         ▼                                  ▼
┌────────────────────────┐      ┌──────────────────────┐
│  特許庁 公式API        │      │  Slack Webhook       │
│  Patent Search API     │      │  (通知送信)          │
│  (APIv1)              │      │                      │
└────────────────────────┘      └──────────────────────┘
```

## データフロー詳細

### 1. トリガー段階

**EventBridge ルール**

```json
{
  "Name": "patent-agent-daily-schedule",
  "ScheduleExpression": "cron(0 20 * * ? *)",
  "State": "ENABLED",
  "Targets": [
    {
      "Arn": "arn:aws:lambda:ap-northeast-1:ACCOUNT_ID:function:patent-agent",
      "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role"
    }
  ]
}
```

毎日20:00 JST に Lambda 関数がトリガーされます。

### 2. 初期化段階

**handler.py**

```python
# 1. 環境変数から認証情報を読み込み
jpo_api_id = get_env_var('JPO_API_ID')
jpo_api_password = get_env_var('JPO_API_PASSWORD')

# 2. CSV から検索キーワードを読み込み
keywords = load_keywords_from_csv(keywords_csv_path)

# 3. PatentAPIClient インスタンス化
api_client = PatentAPIClient(api_id, api_password, token_url)
```

### 3. API認証段階

**patent_api.py::PatentAPIClient.get_access_token()**

```
POST https://ip-data.jpo.go.jp/auth/token
Authorization: Basic (base64(JPO_API_ID:JPO_API_PASSWORD))

レスポンス:
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

トークンは毎回新規取得されるため、有効期限切れの心配がありません。

### 4. 特許検索段階

**patent_api.py::PatentAPIClient.search_patents()**

各キーワードに対して以下のリクエストを実行：

```
POST https://ip-data.jpo.go.jp/api/1/search
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "term": "保険",
  "start": 1,
  "rows": 50
}
```

レスポンス例：

```json
{
  "results": [
    {
      "patentNumber": "JP2026000001",
      "title": "保険商品の販売方法",
      "applicant": "株式会社ABC",
      "publicationDate": "2026-05-30",
      "abstract": "..."
    },
    ...
  ]
}
```

### 5. データ処理段階

```python
# 複数キーワードの検索結果を統合
all_patents = []
for patents in search_results.values():
    all_patents.extend(patents)

# 重複排除（patent_number で一意性を確保）
deduplicated = deduplicate_patents(all_patents)
```

### 6. 通知段階

**slack_notifier.py::SlackNotifier.send_patent_notification()**

```
POST https://hooks.slack.com/services/T0AJT7CGYBZ/B0B71DVAMT5/...

{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "特許情報取得レポート"
      }
    },
    ...
  ]
}
```

## モジュール設計

### handler.py
- **責務**: Lambda エントリーポイント、全体フロー制御
- **依存**: patent_api, slack_notifier, utils
- **入力**: AWS Lambda event（利用しない）
- **出力**: {statusCode, body}

### patent_api.py
- **責務**: 特許庁APIとの通信・認証
- **クラス**: PatentAPIClient
  - `get_access_token()`: トークン取得
  - `search_patents(keyword)`: キーワード検索
  - `search_multiple_keywords(keywords)`: 複数キーワード検索

### slack_notifier.py
- **責務**: Slack Webhook通知
- **クラス**: SlackNotifier
  - `send_patent_notification()`: 通知送信
  - `_build_results_message()`: メッセージ組立（結果あり）
  - `_build_no_results_message()`: メッセージ組立（結果なし）
  - `_format_patent()`: 特許情報フォーマット

### utils.py
- **責務**: 共通ユーティリティ
- **関数**:
  - `get_env_var()`: 環境変数取得
  - `load_keywords_from_csv()`: CSV読み込み
  - `deduplicate_patents()`: 重複排除
  - `log_error()`: エラーログ

## エラーハンドリング戦略

### API認証エラー
```python
try:
    self.get_access_token()
except requests.exceptions.RequestException as e:
    logger.error(f"Failed to obtain access token: {str(e)}")
    raise
```
→ 認証失敗時はLambda実行を中断し、CloudWatch Logsに記録

### 特許検索エラー
```python
try:
    response = requests.post(search_url, ...)
except requests.exceptions.RequestException as e:
    logger.error(f"Patent search failed for '{keyword}': {str(e)}")
    return []
```
→ 検索失敗時は空リストを返し、処理を継続

### Slack通知エラー
```python
try:
    response = requests.post(self.webhook_url, ...)
except requests.exceptions.RequestException as e:
    logger.error(f"Failed to send Slack notification: {str(e)}")
    return False
```
→ 通知失敗時は False を返し、CloudWatch Logs に記録

## スケーリングと拡張性

### 複数のキーワードセット管理
将来的に異なるカテゴリーの検索を行う場合：

```
src/config/
├── keywords_insurance.csv
├── keywords_pharma.csv
└── keywords_tech.csv
```

各CSVに対応したLambda関数を作成、または handler.py を改修

### 新しい通知チャネルの追加
Slack以外にメール通知を追加する場合：

```python
# slack_notifier.py と同層に email_notifier.py を作成
from email_notifier import EmailNotifier

# handler.py で並列処理
notifier_slack = SlackNotifier(webhook_url)
notifier_email = EmailNotifier(email_config)

notifier_slack.send_patent_notification(results)
notifier_email.send_patent_notification(results)
```

### 新しいAPI源の追加
Google Patents など別のAPI源を追加：

```python
# patent_api.py と同層に google_patents_api.py を作成
from patent_api import PatentAPIClient
from google_patents_api import GooglePatentsClient

# handler.py で並列実行
jpo_results = api_client.search_multiple_keywords(keywords)
google_results = google_client.search_multiple_keywords(keywords)

combined_results = {**jpo_results, **google_results}
```

## セキュリティ設計

### フェーズ1（ローカル検証）
- `.env` ファイルで認証情報を管理
- `.gitignore` で `.env` をリポジトリから除外
- ローカルマシンのみで実行

### フェーズ2（本番環境）
- AWS Secrets Manager で認証情報を管理

```python
import boto3

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='patent-agent/jpo-api')
    return json.loads(response['SecretString'])

# 使用
secret = get_secret()
api_id = secret['JPO_API_ID']
api_password = secret['JPO_API_PASSWORD']
```

- Lambda IAM ロール: `secretsmanager:GetSecretValue` 権限付与
- S3 バケット: プライベート設定、VPC エンドポイント利用（オプション）

### ネットワークセキュリティ
- Lambda VPC内配置（オプション）
- APIゲートウェイ経由のアクセス（オプション）
- CloudTrail で API 呼び出しを監査

## 運用とモニタリング

### CloudWatch Logs
Lambda が生成するログはCloudWatch Logsに自動保存：

```
/aws/lambda/patent-agent
```

### ログレベル設定
```python
logger.setLevel(logging.INFO)  # INFO以上のログを記録
```

記録される主なイベント：
- トークン取得成功
- キーワード読み込み
- 検索実行結果
- 特許数
- Slack通知成功/失敗

### アラート設定（推奨）
CloudWatch Alarms で以下を監視：

- Lambda 実行失敗
- Slack通知失敗
- 実行時間異常

## コスト最適化

### AWS 費用試算（月額）
- EventBridge: ~$0.36（毎日1回実行）
- Lambda: ~$0.20（毎回1秒実行、無料枠内）
- Secrets Manager: $0.40（スタンダードシークレット1個）

**合計: ~$1.00/月**（S3使用料別）

## トラブルシューティング

### Lambda がタイムアウト
特許庁APIのレスポンスが遅い場合、Lambda タイムアウト値を増加：
- デフォルト: 3分
- 推奨: 5分

### 検索結果が多い
特許数が多い場合、CSV の `rows` パラメータを削減：

```python
patents = self.search_patents(keyword, max_results=20)  # 50 から 20 に削減
```

### Slack メッセージが長い
特許数が多い場合、1キーワードあたり表示件数を削減：

```python
for idx, patent in enumerate(patents[:3]):  # 5 から 3 に削減
    # ...
```

## 参考情報

- [特許庁 データAPI](https://ip-data.jpo.go.jp/pages/top.html)
- [AWS Lambda 価格](https://aws.amazon.com/jp/lambda/pricing/)
- [AWS EventBridge](https://aws.amazon.com/jp/eventbridge/)
- [Slack API - Webhooks](https://api.slack.com/messaging/webhooks)
