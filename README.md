# nlsm-lax-agent

2次元非線形シグマ模型のLax接続候補を探索し、記号計算による検証結果と探索履歴を保存するためのプロジェクトです。

現在は設計段階です。エージェント本体、物理計算ライブラリ、以下の設定を読み込む実行コマンドはまだ実装されていません。

| 文書 | 内容 |
| --- | --- |
| [アーキテクチャ](docs/architecture.ja.md) | LangGraph、LLMバックエンド、ツール、データ、実行管理の設計 |
| [物理検証](docs/verification.ja.md) | 入力の定義、零曲率条件、運動方程式の回収、判定の適用範囲 |
| [実装計画](docs/implementation-plan.ja.md) | 実装順序、受入条件、比較実験、研究段階への移行条件 |
| [設定例](examples/configs/) | オフライン、クラウド、ローカル推論の設定案 |

初期構成はPython、SymPy、Pydantic、LangGraph、LiteLLM、SQLiteです。LangGraphが探索の進行を管理し、LiteLLMがLLMへの接続を切り替えます。物理計算はLLMやLangGraphから独立したPython関数として提供し、同じ関数をコマンドラインとModel Context Protocol（MCP）から利用できるようにします。

検証結果には適用条件を付けます。零曲率条件と運動方程式の同値性、スペクトルパラメータの本質性、保存量のPoisson可換性は別々に記録します。探索の失敗から模型の非可積分性を結論しません。
