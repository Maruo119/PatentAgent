# AWS セットアップ手順書

このドキュメントでは、PatentAgent を AWS 上にデプロイするための詳細な手順を説明します。

## 前提条件

- AWS アカウントが作成済み
- AWS CLI がインストール済み
- IAM ユーザーが作成済み（AdministratorAccess または同等の権限）
- 「ローカル検証（フェーズ1）」が完了し、動作が確認済み

## セットアップ概要

```
1. IAM ロール作成
   ↓
2. Lambda 関数作成
   ↓
3. EventBridge ルール作成
   ↓
4. S3 バケット作成（オプション）
   ↓
5. 環境変数設定
   ↓
6. テスト実行
```

---

## Step 1: IAM ロール作成

### 1-1. Lambda 実行ロール作成

AWS マネジメントコンソール → IAM → ロール → ロールを作成

**信頼される エンティティ：**
- サービス: Lambda

**ポリシー：**

以下の2つのインラインポリシーを追加してください。

#### ポリシー1: CloudWatch Logs への書き込み

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:ap-northeast-1:*:*"
        }
    ]
}
```

#### ポリシー2: S3 からの読み取り（後続フェーズ）

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::patent-agent-config/*"
        }
    ]
}
```

#### ポリシー3: Secrets Manager からの読み取り（フェーズ2）

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:ap-northeast-1:*:secret:patent-agent/*"
        }
    ]
}
```

**ロール名：** `patent-agent-lambda-execution-role`

---

## Step 2: Lambda 関数作成

### 2-1. Lambda 関数を作成

AWS マネジメントコンソール → Lambda → 関数を作成

**基本情報：**
- 関数名: `patent-agent`
- ランタイム: `Python 3.11`
- 実行ロール: 上記で作成した `patent-agent-lambda-execution-role`
- タイムアウト: 5 分（300秒）
- メモリ: 512 MB

### 2-2. コードをアップロード

ローカルマシンで、Lambda 用の ZIP ファイルを作成：

```powershell
# PatentAgent ディレクトリで実行
cd src/lambda

# 依存パッケージをインストール
pip install -r ../../requirements.txt -t .

# ZIP ファイル作成
# Windows PowerShell
Compress-Archive -Path . -DestinationPath lambda_function.zip

# または Linux/Mac
# zip -r lambda_function.zip .
```

**AWS Lambda コンソールで：**

1. 「コード」タブ → 「コードをアップロード」
2. 上記で作成した `lambda_function.zip` をアップロード
3. ハンドラー：`handler.lambda_handler` を設定

### 2-3. レイヤーで依存パッケージを管理（代替案）

依存パッケージを Lambda レイヤーで管理することも可能です：

```powershell
# レイヤー用ディレクトリ構造を作成
mkdir python
pip install -r requirements.txt -t python/

# ZIP 作成
Compress-Archive -Path python -DestinationPath layer.zip
```

Lambda コンソール → レイヤー → レイヤーを作成

- 名前: `patent-agent-dependencies`
- 互換ランタイム: `Python 3.11`
- ZIP ファイルをアップロード

その後、Lambda 関数 → レイヤー → レイヤーを追加で上記を指定

---

## Step 3: 環境変数設定

### 3-1. Lambda 関数に環境変数を設定

Lambda コンソール → 関数選択 → 設定 → 環境変数 → 編集

**以下の環境変数を追加：**

| キー | 値 |
|------|-----|
| `JPO_API_ID` | `b2rw9is.rv-n` |
| `JPO_API_PASSWORD` | `9ad6anrr_ne4` |
| `JPO_TOKEN_URL` | `https://ip-data.jpo.go.jp/auth/token` |
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/services/YOUR_WEBHOOK_URL` |

---

## Step 4: S3 バケット作成（オプション・推奨）

### 4-1. S3 バケット作成

AWS マネジメントコンソール → S3 → バケットを作成

**バケット設定：**
- バケット名: `patent-agent-config-ACCOUNT_ID` （ユニークな名前）
- リージョン: `ap-northeast-1`
- ブロックパブリックアクセス: すべてオン
- バージョニング: 有効化

### 4-2. keywords.csv をアップロード

作成したバケットに `src/config/keywords.csv` をアップロード

### 4-3. Lambda にバケットアクセス権限を付与

IAM → ロール → `patent-agent-lambda-execution-role` → インラインポリシー追加

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::patent-agent-config-ACCOUNT_ID/*"
        }
    ]
}
```

### 4-4. Lambda コードを S3 対応に修正

`src/lambda/handler.py` を修正：

```python
import boto3
from botocore.exceptions import ClientError

def get_keywords_from_s3():
    """S3 から keywords.csv を取得"""
    s3 = boto3.client('s3')
    bucket_name = 'patent-agent-config-ACCOUNT_ID'
    key = 'keywords.csv'
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        return parse_csv(csv_content)
    except ClientError as e:
        logger.error(f"Failed to get keywords from S3: {str(e)}")
        raise

def lambda_handler(event, context):
    # ...
    # keywords = load_keywords_from_csv(keywords_csv_path)  # ← この行を置換
    keywords = get_keywords_from_s3()  # S3から読み込み
    # ...
```

---

## Step 5: EventBridge ルール作成

### 5-1. EventBridge コンソールで新規ルール作成

AWS マネジメントコンソール → EventBridge → ルール → ルールを作成

**ルール名：** `patent-agent-daily-schedule`

### 5-2. ルール定義

**ルールの種類：** スケジュール

**スケジュール式：**

```
cron(0 20 * * ? *)
```

- `0` - 分（0分）
- `20` - 時間（20時 = 午後8時）
- `*` - 日（毎日）
- `*` - 月（毎月）
- `?` - 曜日（指定なし）
- `*` - 年（毎年）

**JST 20:00 = UTC 11:00 に実行されます**

### 5-3. ターゲット設定

**ターゲット：** Lambda 関数

- 関数: `patent-agent`
- 実行ロール: 新規ロール作成（EventBridge用）

**EventBridge 用 IAM ロール ポリシー：**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": "arn:aws:lambda:ap-northeast-1:ACCOUNT_ID:function:patent-agent"
        }
    ]
}
```

### 5-4. ルールを有効化

「ルールの詳細」で「状態」を「有効」に設定

---

## Step 6: テスト実行

### 6-1. Lambda コンソールでテスト

Lambda 関数 → テスト → テストイベント作成

**テストイベント名：** `test-patent-agent`

**イベント JSON：**

```json
{}
```

「テスト」ボタンをクリック

### 6-2. 実行結果確認

**成功時の出力例：**

```
Response:
{
    "statusCode": 200,
    "body": "{\"message\": \"Successfully retrieved and sent patent information\", \"patents_found\": 15}"
}
```

### 6-3. CloudWatch Logs で詳細ログを確認

Lambda → 関数 → モニタリング → CloudWatch Logs で詳細なログを確認

---

## フェーズ2: AWS Secrets Manager への移行

### Step 1: Secrets Manager にシークレット登録

AWS マネジメントコンソール → Secrets Manager → シークレットを保存

**シークレット名：** `patent-agent/jpo-api`

**シークレット値（JSON）：**

```json
{
  "JPO_API_ID": "b2rw9is.rv-n",
  "JPO_API_PASSWORD": "9ad6anrr_ne4"
}
```

### Step 2: Lambda コードを修正

`src/lambda/handler.py` を修正：

```python
import boto3
import json
from botocore.exceptions import ClientError

def get_jpo_credentials():
    """AWS Secrets Manager から JPO API 認証情報を取得"""
    client = boto3.client('secretsmanager', region_name='ap-northeast-1')
    
    try:
        response = client.get_secret_value(SecretId='patent-agent/jpo-api')
        secret = json.loads(response['SecretString'])
        return secret['JPO_API_ID'], secret['JPO_API_PASSWORD']
    except ClientError as e:
        logger.error(f"Failed to retrieve secret: {str(e)}")
        raise

def lambda_handler(event, context):
    # ...環境変数ではなく Secrets Manager から取得
    jpo_api_id, jpo_api_password = get_jpo_credentials()
    # ...
```

### Step 3: IAM ロールに権限追加

IAM → ロール → `patent-agent-lambda-execution-role` → インラインポリシー追加

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:ap-northeast-1:ACCOUNT_ID:secret:patent-agent/jpo-api-*"
        }
    ]
}
```

### Step 4: 環境変数から削除

Lambda コンソール → 設定 → 環境変数から `JPO_API_ID` と `JPO_API_PASSWORD` を削除

---

## トラブルシューティング

### Lambda がタイムアウト

**症状：** Task timed out after X seconds

**原因：** 特許庁APIのレスポンスが遅い

**対処：**
1. Lambda 設定 → タイムアウト値を 5分 に増加
2. または、特許庁APIの検索結果件数を削減

### Slack 通知が送信されない

**症状：** Lambda は正常終了だが、Slack に通知がない

**対処：**
1. CloudWatch Logs を確認
2. Slack Webhook URL が正しいか確認
3. Slack ワークスペースの Webhook 設定を確認

### S3 からの読み込みエラー

**症状：** AccessDenied エラー

**対処：**
1. IAM ロールに S3 読み取り権限があるか確認
2. バケット名が正しいか確認
3. keywords.csv ファイルが存在するか確認

### EventBridge ルールが実行されない

**症状：** 定期実行が開始されない

**対処：**
1. EventBridge コンソール → ルール → 「状態」が「有効」か確認
2. スケジュール式が正しいか確認（cron(0 20 * * ? *)）
3. CloudWatch Events のメトリクスで実行記録を確認

---

## セキュリティベストプラクティス

### 環境変数の保護

- `.env` ファイルは `.gitignore` に含める
- GitHub に `.env` をコミットしない
- Secrets Manager で本番環境の認証情報を管理

### IAM 権限の最小化

- Lambda 実行ロール: 必要な権限のみを付与
- S3 バケット: プライベート設定（ブロックパブリックアクセス有効）
- Secrets Manager: 最小権限の原則

### ログの監視

- CloudWatch Logs で定期的にログを確認
- エラーログを監視（CloudWatch Alarms で自動アラート）
- CloudTrail で API 呼び出しを監査

---

## コスト削減のヒント

### Lambda 関数の最適化

- メモリ: 512 MB から 256 MB に削減（実行時間が増加する可能性）
- 実行時間: 不要な待機を削除
- タイムアウト: 必要最小限に設定

### S3 ストレージ削減

- keywords.csv は小さいファイルのため無視できるコスト
- バージョニングは必要に応じて有効化

### EventBridge 最適化

- スケジュール式: 毎日1回のみ（十分な頻度）
- ターゲット: Lambda 関数のみ（不要なターゲットは削除）

---

## 監視・アラート設定（推奨）

### CloudWatch Alarms 作成

#### Lambda 実行失敗アラーム

```json
{
    "AlarmName": "patent-agent-lambda-errors",
    "MetricName": "Errors",
    "Namespace": "AWS/Lambda",
    "Statistic": "Sum",
    "Period": 300,
    "EvaluationPeriods": 1,
    "Threshold": 1,
    "ComparisonOperator": "GreaterThanOrEqualToThreshold",
    "AlarmActions": ["arn:aws:sns:ap-northeast-1:ACCOUNT_ID:alert-topic"]
}
```

#### Lambda 実行時間異常アラーム

```json
{
    "AlarmName": "patent-agent-lambda-duration",
    "MetricName": "Duration",
    "Namespace": "AWS/Lambda",
    "Statistic": "Average",
    "Period": 300,
    "EvaluationPeriods": 1,
    "Threshold": 60000,
    "ComparisonOperator": "GreaterThanThreshold",
    "AlarmActions": ["arn:aws:sns:ap-northeast-1:ACCOUNT_ID:alert-topic"]
}
```

---

## 参考リソース

- [AWS Lambda - Python ランタイム](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [AWS EventBridge - スケジュール式](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Slack API - Incoming Webhooks](https://api.slack.com/messaging/webhooks)
