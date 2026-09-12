# nlsm-lax-agent

2次元非線形シグマ模型のLax接続を探索・検証する研究用ソフトウェアです。初期実装はSU(2)主カイラル模型（PCM）を対象とし、記号計算ツール、MCPサーバー、LangGraph＋LiteLLMによる付属エージェントを含みます。

<a name="quickstart"></a>

## 最初に動かす

設計上の位置づけ：[初期版の利用方法](docs/02-external-design/external-design.ja.md#design-pcm-implementation)。検証方法：[PCMの検証処理](docs/03-internal-design/pcm-verification.ja.md#verification-scope)。

Python 3.11以降の仮想環境で、リポジトリ直下から実行します。

```bash
python -m pip install -e '.[agent,mcp]'
nlsm-lax demo --output runs/pcm-demo.json
nlsm-lax recheck runs/pcm-demo.json
```

`demo` は提案を固定した動作確認です。言語モデルを使わず、カレント自身の候補の不備を受けて別のansatzの未定係数を解き、検証・保存まで進めます。LLMの探索能力を測る実験ではありません。`recheck` は保存した入力から物理計算を再実行し、元の結果と比較します。

実際の付属エージェントは、[ローカル推論の設定例](examples/local.toml)のモデル名を起動済みサーバーに合わせて指定し、次で動かします。

```bash
nlsm-lax agent examples/local.toml --output runs/local-result.json
```

Geminiには[設定例](examples/gemini.toml)を使い、利用できるモデル名と環境変数 `GEMINI_API_KEY` を設定します。無料枠のプロジェクトかどうかは利用者側のGoogle設定で確認します。APIキーを文書や実行記録へ書き込む必要はありません。接続エラーや利用上限に達した場合は記録を保存して停止します。

停止・方向変更・再開は次の操作で行います。`RUN_ID` は開始時・終了時の表示または保存した記録にある実行番号です。

```bash
nlsm-lax show RUN_ID
nlsm-lax stop RUN_ID
nlsm-lax agent examples/local.toml --resume RUN_ID --direction 'スペクトル依存を有理関数として再検討する'
```

停止要求は次の処理の開始前に反映します。計算中の処理は1回の時間上限までに終了させます。予算を使い切った実行を再開するときは、同じ設定ファイルの上限を変更します。消費済みの回数と履歴は保持します。

Pythonでは数式から入力を組み立てられます。

```python
from nlsm_lax_agent import pcm_model, scalar_candidate, verify_candidate

# S = prefactor * integral dx_plus dx_minus tr(j_plus j_minus), g in SU(2).
model = pcm_model("-1/(2*kappa**2)")
candidate = scalar_candidate("1/(1-z)", "1/(1+z)")
result = verify_candidate(candidate, model)
assert result["status"] == "verified"
```

[Pythonの計算例](examples/pcm_python.py)にはEOM導出と未定係数の求解もあります。現在受け付ける作用は上記PCM、候補はカレントに線形でスペクトルパラメータの有理関数を係数とするものです。任意のLaTeXの自動解釈や、T¹,¹・ABL・変形模型への対応は未実装です。

外部エージェントから使う場合は `nlsm-lax-mcp` をMCPのstdioサーバーとして登録します。[MCP設定例](examples/mcp.json)の実行ファイルが見つからない環境では、インストール先の絶対パスを指定します。MCPサーバーの起動に付属エージェントやLLMの設定は不要です。

確認済みの[実行記録](examples/results/pcm-demo.json)を同梱しています。上記の `recheck` にこのファイルを指定して再検算できます。計算履歴と応答履歴を保持し、イベントごとの状態の重複だけを省いた例です。

自動試験30件とwheelのビルドを確認済みです。試験範囲は、記号計算、固定提案による探索ループ、MCPの実通信、模擬応答サーバーを使ったLiteLLMのHTTP接続です。実際のGemini・ローカル言語モデルによる探索能力は未評価です。

<a name="documentation"></a>

## 文書の順序

フォルダ名の先頭の番号が、要件定義 → 外部設計 → 内部設計の順序を表します。

| 段階 | フォルダ | 決めること | 現在の状態 |
| --- | --- | --- | --- |
| 1. 要件定義 | `docs/01-requirements/` | 誰が何に使い、どの機能と結果を必要とするか | [要件定義書](docs/01-requirements/requirements.ja.md)にヒアリング結果と初期版の範囲を反映 |
| 2. 外部設計 | `docs/02-external-design/` | 利用者から見た操作、入出力、利用条件 | [既存案](docs/02-external-design/external-design.ja.md)を初期版の一連の利用場面に合わせて具体化する |
| 3. 内部設計 | `docs/03-internal-design/` | 内部の構成と役割、データ構造、数式の規約、処理と判定の手順 | [入力設計](docs/03-internal-design/model-input.ja.md#detail-scope)と[PCM検証処理](docs/03-internal-design/pcm-verification.ja.md#verification-scope)に実装範囲を明記 |
| 4. 実装・試験 | `src/`、`tests/`、`examples/` | 実行可能な機能とその確認 | PCMの初期実装。[初期版の受入条件](docs/01-requirements/requirements.ja.md#req-initial-acceptance)のうち実モデル接続などは未確認 |

ヒアリングで整理した[現在の作業](docs/01-requirements/requirements.ja.md#req-as-is)と[期待する成果](docs/01-requirements/requirements.ja.md#req-to-be)を設計の基準にします。一度に確認する文書は一つとし、上位の内容を確認してから次へ進みます。工程の移行条件は[現在開発する範囲](docs/01-requirements/requirements.ja.md#req-development)に適用し、その範囲の設計が整ったら実装します。各文書の見出し、要件、操作などの項目には直接参照できるリンク先を設けます。対応関係を記すときは参照先の項目へリンクし、参照先にも元の項目へ戻るリンクを付けます。文書を追加・変更するときは、両方向のリンクも更新します。内部の変数名や関数名は内部設計で定義し、要件の説明には持ち込みません。

文書間では相対リンクを使い、表の項目には[GitHubのカスタムアンカー](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#custom-anchors)を付けます。リンク先の名前は見出しの表現変更でも維持し、参照切れと対応する戻りリンクを確認します。後続の設計が未作成の項目は、その状態を明記します。

数式はインラインにドル記号とバッククオートを組み合わせた形式、独立した数式に `$$...$$` を使います。トレースと対角行列の表記は `\mathrm{tr}`、`\mathrm{diag}` とします。

## 参考資料

[以前の設計案・文献調査](docs/archive/README.md)は参考資料として保存しています。現在の要件定義とは分けて扱い、必要な内容を各段階で取り出して整理します。
