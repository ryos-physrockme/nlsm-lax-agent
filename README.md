# nlsm-lax-agent

2次元非線形シグマ模型のLax接続の候補を探索し、検証するための研究用ソフトウェアです。現在はヒアリング結果を要件定義に反映し、最初に動く範囲を具体化する段階で、計算ライブラリとエージェントは未実装です。

まず読む文書は、[要件定義](docs/01-requirements/requirements.ja.md)です。

現在の確認対象は、要件定義の[現在の作業と課題](docs/01-requirements/requirements.ja.md#req-as-is)、[期待する成果](docs/01-requirements/requirements.ja.md#req-to-be)、[開発順序と移行条件](docs/01-requirements/requirements.ja.md#req-development)です。最初の到達点は、PCMで候補の提案・計算・検証・再試行まで動く付属エージェントと、Python・MCPから利用できる共通ツールです。

<a name="documentation"></a>

## 文書の順序

フォルダ名の先頭の番号が、要件定義 → 外部設計 → 内部設計の順序を表します。

| 段階 | フォルダ | 決めること | 現在の状態 |
| --- | --- | --- | --- |
| 1. 要件定義 | `docs/01-requirements/` | 誰が何に使い、どの機能と結果を必要とするか | [要件定義書](docs/01-requirements/requirements.ja.md)にヒアリング結果と初期版の範囲を反映 |
| 2. 外部設計 | `docs/02-external-design/` | 利用者から見た操作、入出力、利用条件 | [既存案](docs/02-external-design/external-design.ja.md)を初期版の一連の利用場面に合わせて具体化する |
| 3. 内部設計 | `docs/03-internal-design/` | 内部の構成と役割、データ構造、数式の規約、処理と判定の手順 | [入力の既存案](docs/03-internal-design/model-input.ja.md#detail-scope)を保持し、初期版の外部設計と整合させる |
| 4. 実装・試験計画 | 未作成 | 作る順序と、各要件を満たしたことの確認方法 | [初期版の受入条件](docs/01-requirements/requirements.ja.md#req-initial-acceptance)に対応する設計から実装する |

ヒアリングで整理した[現在の作業](docs/01-requirements/requirements.ja.md#req-as-is)と[期待する成果](docs/01-requirements/requirements.ja.md#req-to-be)を設計の基準にします。一度に確認する文書は一つとし、上位の内容を確認してから次へ進みます。工程の移行条件は[現在開発する範囲](docs/01-requirements/requirements.ja.md#req-development)に適用し、その範囲の設計が整ったら実装します。各文書の見出し、要件、操作などの項目には直接参照できるリンク先を設けます。対応関係を記すときは参照先の項目へリンクし、参照先にも元の項目へ戻るリンクを付けます。文書を追加・変更するときは、両方向のリンクも更新します。内部の変数名や関数名は内部設計で定義し、要件の説明には持ち込みません。

文書間では相対リンクを使い、表の項目には[GitHubのカスタムアンカー](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#custom-anchors)を付けます。リンク先の名前は見出しの表現変更でも維持し、参照切れと対応する戻りリンクを確認します。後続の設計が未作成の項目は、その状態を明記します。

数式はインラインにドル記号とバッククオートを組み合わせた形式、独立した数式に `$$...$$` を使います。トレースと対角行列の表記は `\mathrm{tr}`、`\mathrm{diag}` とします。

## 参考資料

[以前の設計案・文献調査](docs/archive/README.md)は参考資料として保存しています。現在の要件定義とは分けて扱い、必要な内容を各段階で取り出して整理します。
