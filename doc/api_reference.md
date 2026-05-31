# 特許庁 公式API 参考情報

本ドキュメントは、PatentAgent で使用する特許庁公式 API（Japan Patent Office Data API）の仕様情報をまとめたものです。

## API概要

**提供機関：** 独立行政法人 国立研究開発機構 科学技術振興機構（JST）

**API公式サイト：** https://ip-data.jpo.go.jp/pages/top.html

**ベースURL：** `https://ip-data.jpo.go.jp/`

## エンドポイント一覧

### 1. アクセストークン取得

**エンドポイント：** `POST /auth/token`

**認証方式：** Basic Authentication

```bash
curl -X POST https://ip-data.jpo.go.jp/auth/token \
  -u "b2rw9is.rv-n:9ad6anrr_ne4"
```

**レスポンス例：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**レスポンスパラメータ：**

| パラメータ | 型 | 説明 |
|----------|-----|------|
| `access_token` | string | JWT形式のアクセストークン |
| `token_type` | string | トークンタイプ（常に "Bearer"） |
| `expires_in` | integer | トークン有効期限（秒） |

**有効期限：** 1時間（3600秒）

### 2. 特許検索

**エンドポイント：** `POST /api/1/search`

**認証方式：** Bearer Token

```bash
curl -X POST https://ip-data.jpo.go.jp/api/1/search \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "term": "保険",
    "start": 1,
    "rows": 50
  }'
```

**リクエストボディ：**

| パラメータ | 型 | 必須 | 説明 | デフォルト | 最大値 |
|----------|-----|------|------|----------|--------|
| `term` | string | ○ | 検索キーワード | - | - |
| `start` | integer | | 結果の開始番号 | 1 | - |
| `rows` | integer | | 取得件数 | 10 | 100 |

**レスポンス例：**

```json
{
  "results": [
    {
      "patentNumber": "JP2026000001",
      "title": "保険商品の販売方法",
      "applicant": "株式会社ABC",
      "publicationDate": "2026-05-30",
      "filingDate": "2025-05-30",
      "abstract": "本発明は、オンラインプラットフォームを利用した保険商品の販売方法に関する...",
      "inventor": ["山田太郎", "鈴木花子"],
      "ipc": ["G06F", "G06Q"],
      "cpc": ["G06Q10/0833"],
      "url": "https://ipforce.jp/patent/JP2026000001"
    },
    ...
  ],
  "totalCount": 500
}
```

**レスポンスパラメータ：**

| パラメータ | 型 | 説明 |
|----------|-----|------|
| `results` | array | マッチした特許情報の配列 |
| `totalCount` | integer | マッチした特許の総数 |

**特許情報オブジェクト：**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `patentNumber` | string | 特許番号（例：JP2026000001） |
| `title` | string | 発明の名称 |
| `applicant` | string | 出願人 |
| `publicationDate` | string | 公開日（YYYY-MM-DD） |
| `filingDate` | string | 出願日（YYYY-MM-DD） |
| `abstract` | string | 要約 |
| `inventor` | array | 発明者名の配列 |
| `ipc` | array | IPC分類（国際特許分類） |
| `cpc` | array | CPC分類（協力特許分類） |
| `url` | string | 特許詳細ページのURL |

## 検索キーワード例

### 保険関連キーワード

```csv
keyword,description,expected_matches
保険,全般的な保険    ,high
損害保険,損害保険   ,medium
生命保険,生命保険   ,medium
損保,損害保険の略  ,low
生保,生命保険の略  ,low
医療保険,医療保険   ,medium
火災保険,火災保険   ,low
自動車保険,自動車保険 ,medium
傷害保険,傷害保険   ,low
地震保険,地震保険   ,low
```

## エラー対応

### HTTP ステータスコード

| コード | 説明 | 対処 |
|--------|------|------|
| 200 | OK | 正常 |
| 400 | Bad Request | リクエストパラメータを確認 |
| 401 | Unauthorized | 認証情報が無効（トークン再取得） |
| 403 | Forbidden | アクセス権限なし |
| 404 | Not Found | エンドポイント存在しない |
| 429 | Too Many Requests | レート制限（しばらく待機） |
| 500 | Internal Server Error | API側のエラー |
| 503 | Service Unavailable | メンテナンス中 |

### エラーレスポンス例

**400 Bad Request：**

```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: term"
}
```

**401 Unauthorized：**

```json
{
  "error": "invalid_token",
  "error_description": "Token has expired"
}
```

## レート制限

**制限内容：**
- リクエスト数: 1000リクエスト/時間
- トークン取得: 100回/時間
- バースト: 10リクエスト/秒

**超過時の動作：**
- HTTP 429 レスポンス
- `Retry-After` ヘッダーで再試行時間を指定

**推奨対応：**

```python
import time
import requests

def search_with_retry(api_client, keyword, max_retries=3):
    for attempt in range(max_retries):
        try:
            return api_client.search_patents(keyword)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limit hit. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                raise
    raise Exception(f"Failed after {max_retries} retries")
```

## ベストプラクティス

### 1. トークンキャッシング（非推奨）

毎回新規取得する方が確実：

```python
# 非推奨: 複数回使用するためにトークンをキャッシュ
token = get_access_token()
patents1 = search_patents(keyword1, token)
patents2 = search_patents(keyword2, token)  # ← 有効期限切れの可能性

# 推奨: 毎回新規取得
patents1 = search_patents(keyword1)  # 内部でトークン取得
patents2 = search_patents(keyword2)  # 内部でトークン取得
```

### 2. キーワード検索の最適化

```python
# 非推奨: 長いキーワード
search_patents("保険商品の販売方法に関する技術")  # マッチ数が少ない

# 推奨: シンプルなキーワード
search_patents("保険")  # マッチ数が多い
```

### 3. ページネーション処理

```python
def search_all_patents(keyword, max_results=100):
    all_patents = []
    rows_per_page = 50
    
    for start in range(1, max_results, rows_per_page):
        patents = search_patents(
            keyword,
            start=start,
            rows=rows_per_page
        )
        
        if not patents:
            break
            
        all_patents.extend(patents)
    
    return all_patents
```

### 4. エラーハンドリング

```python
def robust_search(keyword):
    try:
        api_client = PatentAPIClient(api_id, api_password, token_url)
        patents = api_client.search_patents(keyword)
        return patents
    
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for keyword: {keyword}")
        return []
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout for keyword: {keyword}")
        return []
    
    except ValueError as e:
        if "token" in str(e).lower():
            logger.error(f"Token error: {str(e)}")
            return []
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error for keyword {keyword}: {str(e)}")
        raise
```

## 特許情報の理解

### 特許番号形式

```
JP2026000001
├─ JP: 日本特許
├─ 2026: 出願年（平成元年=1989年からのオフセット + 1988）
└─ 000001: 連番
```

### 分類体系

**IPC（International Patent Classification）：** 国際特許分類

```
G06F    - Computing, Calculating, Counting
G06Q    - Data Processing Systems
├─ G06Q10 - Administration, Management
└─ G06Q10/0833 - Insurance
```

**CPC（Cooperative Patent Classification）：** 協力特許分類

```
G06Q10/0833 - Insurance administration
```

## API使用例

### 基本的な検索

```python
from patent_api import PatentAPIClient

# クライアント初期化
client = PatentAPIClient(
    api_id="b2rw9is.rv-n",
    api_password="9ad6anrr_ne4",
    token_url="https://ip-data.jpo.go.jp/auth/token"
)

# トークン取得（自動）
patents = client.search_patents("保険", max_results=50)

# 結果処理
for patent in patents:
    print(f"{patent['patentNumber']}: {patent['title']}")
    print(f"  出願人: {patent['applicant']}")
    print(f"  公開日: {patent['publicationDate']}")
```

### 複数キーワード検索

```python
keywords = ["保険", "損保", "生保"]
results = client.search_multiple_keywords(keywords)

for keyword, patents in results.items():
    print(f"\n{keyword}: {len(patents)} 件")
    for patent in patents[:3]:  # 最初の3件を表示
        print(f"  - {patent['title']}")
```

## トラブルシューティング

### 認証エラー

**エラーメッセージ：** `Invalid credentials`

**原因：** API ID またはパスワードが不正

**対処：**
1. API提供サイト（https://ip-data.jpo.go.jp/pages/top.html）で認証情報を確認
2. 認証情報をコピー＆ペースト（手打ち避け）

### トークン有効期限エラー

**エラーメッセージ：** `Token has expired`

**原因：** トークン有効期限（1時間）切れ

**対処：** 新しいトークンを再取得（PatentAPIClient が自動処理）

### 検索結果が空

**原因1：** キーワードが適切でない

**対処：** より一般的なキーワードを試す

```python
# 不適切: 複合キーワード
search_patents("オンラインプラットフォームを利用した生命保険")

# 改善: シンプルなキーワード
search_patents("保険")
search_patents("生保")
```

**原因2：** 検索対象期間外

**対処：** 日付パラメータがあればそれを確認（現在は非サポート）

### レート制限エラー

**エラーコード：** HTTP 429

**原因：** 短時間に大量リクエスト

**対処：**
1. リクエスト間隔を広げる
2. バッチ処理サイズを削減
3. キーワード数を削減

```python
import time

keywords = ["保険", "損保", "生保", ...]
for keyword in keywords:
    patents = search_patents(keyword)
    time.sleep(2)  # 2秒待機
```

## 参考情報

- **公式ドキュメント：** https://ip-data.jpo.go.jp/pages/top.html
- **API仕様書（PDF）：** https://ip-data.jpo.go.jp/docs/api_specification.pdf
- **利用規約：** https://ip-data.jpo.go.jp/pages/terms.html
- **FAQ：** https://ip-data.jpo.go.jp/pages/faq.html

## よくある質問

**Q. トークンは永続化できますか？**

A. いいえ。トークンは1時間で有効期限切れになります。毎回新規取得してください。

**Q. 商用利用はできますか？**

A. 公式サイトの利用規約を確認してください。一般的には個人・学術的利用が想定されています。

**Q. 検索結果の保存期間は？**

A. API側で保存されません。ユーザー側で必要に応じて保存してください。

**Q. 特許以外の情報（商標、意匠）も取得できますか？**

A. PatentAgent は特許のみを対象としています。他の情報は別途APIを確認してください。

**Q. 日本以外の特許も取得できますか？**

A. 本APIは日本特許庁の情報を提供しています。国際特許については JP2000 以降の国際出願（PCT）を確認してください。
