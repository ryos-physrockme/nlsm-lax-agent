# nlsm-lax-agent

2次元非線形シグマ模型のLax接続候補を探索し、記号計算による検証結果と探索履歴を保存するためのプロジェクトです。

現在は設計段階です。エージェント本体、物理計算ライブラリ、以下の設定を読み込む実行コマンドはまだ実装されていません。

| 文書 | 内容 |
| --- | --- |
| [アーキテクチャ](docs/architecture.ja.md) | LangGraph、LLMバックエンド、ツール、データ、実行管理の設計 |
| [物理検証](docs/verification.ja.md) | 入力の定義、零曲率条件、運動方程式の回収、判定の適用範囲 |
| [機械学習による候補探索](docs/ml-search.ja.md) | 学習対象、探索ツール、厳密な式の復元、検証への接続 |
| [実装計画](docs/implementation-plan.ja.md) | 実装順序、受入条件、比較実験、研究段階への移行条件 |
| [論文評価と設計の点検](docs/research-evaluation.ja.md) | 情報系・物理×AIの先行例、現状との照合、評価実験の計画案 |
| [設定例](examples/configs/) | オフライン、クラウド、ローカル推論の設定案 |

初期構成はPython、SymPy、Pydantic、LangGraph、LiteLLM、SQLiteです。LangGraphが探索の進行を管理し、LiteLLMがLLMへの接続を切り替えます。物理計算はLLMやLangGraphから独立したPython関数として提供し、同じ関数をコマンドラインとModel Context Protocol（MCP）から利用できるようにします。

外部のコーディングエージェントはローカルのMCPサーバーへ接続し、自身で探索を進める設計です。MCPサーバーはLLMを呼ばず、`tools.toml`だけを読みます。組み込みエージェントの開発にはGemini API無料枠とローカル推論を使い、同じ物理ツールをPythonから呼びます。自動テストの既定は`mock`、開発用のAPI費用上限は0米ドルです。

機械学習によるLax候補探索もツールの設計に含めます。PyTorchを任意依存とし、検証器の整備後に数値最適化から着手します。ニューラルネットワークによる係数関数の学習も同じ入出力へ接続する方針です。LLMの追加学習は別の開発段階とします。

検証結果には適用条件を付けます。零曲率条件と運動方程式の同値性、スペクトルパラメータの本質性、保存量のPoisson可換性は別々に記録します。探索の失敗から模型の非可積分性を結論しません。

文書のインライン数式は ``$`...`$`` とし、前後に空白を入れます。独立した数式は `$$...$$` で記述します。[GitHubの数式記法](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions)に従い、式番号は数式ブロック内に `\qquad \text{(1)}` のように付けます。`\tag{...}` を含む数式がGitHubの表示で縦に崩れるため、この文書では使用しません。
