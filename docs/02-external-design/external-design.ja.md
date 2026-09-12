# 外部設計書：利用方法と操作

対象：nlsm-lax-agent。更新日：2026年9月12日。状態：全体設計とPCMの初期実装。実装済みの範囲は第8章に示す。

本書は、2次元非線形シグマ模型のLax接続を探索・検証するソフトウェアについて、利用者が行う操作と、その入力・出力の全体像を定める。[要件定義書](../01-requirements/requirements.ja.md)を上位文書とし、各節と操作から対応する要件へリンクする。要件側にも、対応する設計へのリンクを付ける。[文書一覧と参照の方針](../../README.md#documentation)に従う。

本書は利用方法と操作の全体像を示す。個々の数式の入力形式、対応模型の数理的な条件、資源上限の計測方法、配布手順は、この全体像に対応付けて順に具体化する。

<a name="design-usage"></a>

## 1. 提供するものと利用方法

対応する上位項目：[1. 背景と目的](../01-requirements/requirements.ja.md#req-purpose)、[2. 利用者と利用場面](../01-requirements/requirements.ja.md#req-users)、[6. 外部インターフェース要件](../01-requirements/requirements.ja.md#req-interfaces)、[7.2 開発上の制約](../01-requirements/requirements.ja.md#req-constraints)。

計算ツール群、外部エージェントが接続するためのMCPサーバー、探索を進める付属エージェントを提供する。MCP（Model Context Protocol）は、エージェントがツールの説明と入出力を取得し、計算を呼び出すための通信規約を指す。

| 利用方法 | 利用者が準備するもの | 次の計算を選ぶ主体 | 計算を実行する場所 | 対応する上位項目 |
| --- | --- | --- | --- | --- |
| <a name="use-python"></a>[Pythonから使う](#use-python) | 計算ライブラリとPythonプログラムまたはノートブック | 研究者、または利用者が書いたプログラム | ライブラリを導入した環境 | [手動で計算する](../01-requirements/requirements.ja.md#user-python)、[I-01](../01-requirements/requirements.ja.md#req-i-01) |
| <a name="use-external"></a>[外部エージェントから使う](#use-external) | CodexやClaude CodeなどのMCPクライアントと、MCPサーバーの起動設定 | 外部エージェント | MCPサーバーを起動した環境 | [外部エージェントに計算を依頼する](../01-requirements/requirements.ja.md#user-external)、[I-02](../01-requirements/requirements.ja.md#req-i-02) |
| <a name="use-agent"></a>[付属エージェントから使う](#use-agent) | 計算ライブラリ、付属エージェント、言語モデルの接続設定 | 付属エージェント | 付属エージェントを起動した環境 | [付属エージェントで探索する](../01-requirements/requirements.ja.md#user-agent)、[I-03](../01-requirements/requirements.ja.md#req-i-03)、[C-01](../01-requirements/requirements.ja.md#req-c-01) |

各利用方法から、同じ計算ツール、検証基準、実行記録を使う。MCPサーバーは付属エージェントとその言語モデルの設定を必要とせず、物理計算の依頼を受け付ける。初期のMCP接続は、クライアントがサーバーを起動し、標準入力・標準出力を通じて通信する方式とする。

付属エージェントには、探索の進行を管理するLangGraphと、言語モデルの接続先を切り替えるLiteLLMを用いる。開発時の接続先はGemini APIの無料枠とローカル推論とする。検証・再検算では言語モデルを呼び出さない。機械学習による候補探索は、追加機能を導入して有効にした場合に利用できる。

<a name="design-inputs"></a>

## 2. 入力と計算の記録

入力の内部設計：[入力検査の手順](../03-internal-design/model-input.ja.md#detail-validation)。

対応する上位項目：[5. データ要件](../01-requirements/requirements.ja.md#req-data)、[F-08](../01-requirements/requirements.ja.md#req-f-08)、[N-03](../01-requirements/requirements.ja.md#req-n-03)。

利用者は、模型と計算条件を登録してから、候補の検証や探索を依頼する。登録時に発行する実行番号は、一連の計算の入力、履歴、資源上限をまとめて参照する識別子である。候補を1つ検証するだけの場合も、この単位で記録する。

| 入力 | 指定する内容 | 使用する場面 | 対応する要件・内部設計 |
| --- | --- | --- | --- |
| <a name="input-model"></a>[模型](#input-model) | 作用、場、時空座標、結合定数、適用領域、仮定、境界条件、使用する恒等式 | すべての物理計算 | [F-01](../01-requirements/requirements.ja.md#req-f-01)、[保存する情報：入力](../01-requirements/requirements.ja.md#data-input)、[伝達事項：対応模型の拡大](../01-requirements/requirements.ja.md#handoff-models)、[入力の数学的規約](../03-internal-design/model-input.ja.md#detail-conventions)、[模型入力の詳細](../03-internal-design/model-input.ja.md#detail-model) |
| <a name="input-candidate"></a>[候補の接続](#input-candidate) | 接続の成分、値が属するLie代数、スペクトルパラメータとその領域、補助線形問題のゲージ群、許容する局所ゲージ変換の条件 | 候補の検証 | [F-02](../01-requirements/requirements.ja.md#req-f-02)、[F-11](../01-requirements/requirements.ja.md#req-f-11)、[保存する情報：入力](../01-requirements/requirements.ja.md#data-input)、[入力の数学的規約](../03-internal-design/model-input.ja.md#detail-conventions)、[候補入力の詳細](../03-internal-design/model-input.ja.md#detail-candidate) |
| <a name="input-search"></a>[探索条件](#input-search) | 研究目的、守る制約、結合定数を変える場合はその範囲。具体的な項・関数形・未知係数・次数は、利用者が指定するかエージェントに提案を依頼する | 記号計算・機械学習による探索 | [F-05](../01-requirements/requirements.ja.md#req-f-05)、[F-06](../01-requirements/requirements.ja.md#req-f-06)、[F-12](../01-requirements/requirements.ja.md#req-f-12) |
| <a name="input-execution"></a>[実行条件](#input-execution) | 時間・メモリの上限、保存先、機械学習を使う場合の学習・乱数設定、付属エージェントを使う場合の言語モデル設定と利用上限 | 実行の開始と再開 | [N-03](../01-requirements/requirements.ja.md#req-n-03)、[保存する情報：使用資源と費用](../01-requirements/requirements.ja.md#data-resources)、[伝達事項：実行上限の測定](../01-requirements/requirements.ja.md#handoff-budgets) |

スペクトルパラメータは、時空に依存せず、場や模型の結合定数から独立した補助パラメータである。その依存を除去できないことを、許容する局所ゲージ変換の範囲を明示して検査する。

模型名から入力例を選ぶ場合も、使用する作用と仮定を確認できる形に展開して保存する。入力に不足や未対応の形式がある場合は、対象箇所と理由を返す。運動方程式は登録した模型から導出し、検証ではその全体を参照する。候補の提出者が選んだ方程式の一部を、全体の代わりには使わない。

条件変更では、元の入力と結果を残し、変更後の内容に版を付ける。各候補と検証結果には、対象模型、入力の版、適用条件を対応付ける。同じ探索の候補修正、条件分岐、再試行には同じ実行番号を使用し、消費済みの予算を引き継ぐ。

<a name="design-operations"></a>

## 3. 呼び出せる操作

対応する上位項目：[4. 機能要件](../01-requirements/requirements.ja.md#req-functions)、[6. 外部インターフェース要件](../01-requirements/requirements.ja.md#req-interfaces)。

以下は公開する操作と入出力の概要である。各操作はPythonとMCPから個別に呼び出せ、付属エージェントも同じ操作を使う。プログラム上の関数名と引数の形式は、入出力の設計で定める。

| 操作 | 入力 | 受け取るもの | 対応する要件・内部設計 |
| --- | --- | --- | --- |
| <a name="operation-tools"></a>[利用できるツールを調べる](#operation-tools) | 必要に応じて計算の目的や対象模型 | ツール名、説明、入出力、適用条件、追加ソフトウェアの要否、利用可否 | [N-04](../01-requirements/requirements.ja.md#req-n-04)、[N-05](../01-requirements/requirements.ja.md#req-n-05) |
| <a name="operation-register"></a>[模型と計算条件を登録する](#operation-register) | 模型、実行条件 | 実行番号、保存した入力、入力の不足や未対応箇所 | [F-01](../01-requirements/requirements.ja.md#req-f-01)、[F-08](../01-requirements/requirements.ja.md#req-f-08)、[模型入力の詳細](../03-internal-design/model-input.ja.md#detail-model) |
| <a name="operation-equations"></a>[運動方程式を導出する](#operation-equations) | 実行番号と入力の版 | 運動方程式全体、使用する恒等式、導出に用いた条件 | [F-01](../01-requirements/requirements.ja.md#req-f-01) |
| <a name="operation-verify"></a>[候補を検証する](#operation-verify) | 実行番号、対象模型の版、候補の接続 | [第4章](#design-verification)の3検査の結果、成立条件、根拠、未解決の計算 | [F-02](../01-requirements/requirements.ja.md#req-f-02)、[F-03](../01-requirements/requirements.ja.md#req-f-03)、[F-04](../01-requirements/requirements.ja.md#req-f-04)、[F-11](../01-requirements/requirements.ja.md#req-f-11)、[保存する情報：検証結果](../01-requirements/requirements.ja.md#data-verification) |
| <a name="operation-symbolic"></a>[記号計算で候補を探す](#operation-symbolic) | 実行番号、探索条件 | 得られた候補、検証結果、探索した範囲、終了理由 | [F-05](../01-requirements/requirements.ja.md#req-f-05) |
| <a name="operation-ml"></a>[機械学習で候補を探す](#operation-ml) | 実行番号、探索条件、学習設定 | 数値候補、厳密な数式への変換結果、変換できた候補の検証結果、終了理由 | [F-06](../01-requirements/requirements.ja.md#req-f-06)、[N-04](../01-requirements/requirements.ja.md#req-n-04) |
| <a name="operation-couplings"></a>[Lax接続の存在条件を結合定数について求める](#operation-couplings) | 実行番号、模型族、結合定数と候補の探索範囲、探索方法 | Lax接続を得られた結合定数の条件、その接続、検証済み・未解決・未探索の範囲 | [F-12](../01-requirements/requirements.ja.md#req-f-12)、[保存する情報：模型族の探索結果](../01-requirements/requirements.ja.md#data-family)、[伝達事項：Lax接続の存在条件の探索](../01-requirements/requirements.ja.md#handoff-couplings) |
| <a name="operation-results"></a>[進捗や結果を読む](#operation-results) | 実行番号、必要に応じて計算番号や取得する結果の指定 | 進捗、残予算、候補、検証結果、根拠となる数式、履歴 | [F-08](../01-requirements/requirements.ja.md#req-f-08)、[F-13](../01-requirements/requirements.ja.md#req-f-13)、[保存する情報：実行条件と履歴](../01-requirements/requirements.ja.md#data-history) |
| <a name="operation-control"></a>[停止・条件変更・再開を行う](#operation-control) | 実行番号、操作、変更する条件と理由 | 操作の受付状況、変更前後の条件、保存済みの進捗、再開する計算 | [F-07](../01-requirements/requirements.ja.md#req-f-07)、[F-10](../01-requirements/requirements.ja.md#req-f-10)、[F-13](../01-requirements/requirements.ja.md#req-f-13)、[保存する情報：人の介入](../01-requirements/requirements.ja.md#data-intervention)、[伝達事項：実行中の人の介入](../01-requirements/requirements.ja.md#handoff-intervention) |
| <a name="operation-records"></a>[記録を出力・再検算する](#operation-records) | 実行番号、出力対象、または保存された記録 | 別環境へ渡せる入力・結果・実行条件、再検算の結果と元の結果との差 | [F-08](../01-requirements/requirements.ja.md#req-f-08)、[F-09](../01-requirements/requirements.ja.md#req-f-09)、[R-03](../01-requirements/requirements.ja.md#req-r-03)、[受入確認：保存した結果の再検算](../01-requirements/requirements.ja.md#accept-recheck) |

[模型と計算条件の登録](#operation-register)では、入力と資源上限を保存し、以後の計算結果を対応付ける記録を用意する。登録後に、運動方程式の導出、候補の検証、探索などの操作を呼び出す。

[結合定数についてLax接続の存在条件を求める操作](#operation-couplings)では、結合定数を変えながら、指定した候補の形で[第4章](#design-verification)の3検査を満たす接続が得られる条件を求める。例えば、ある模型族で2つの結合定数が等しい場合に接続を得られれば、その等式と接続を返す。一般には等式・不等式などの条件と、その条件の下で検証した接続を返す。結果では、検証済みの領域、探索しても判定できなかった領域、未探索の領域を区別して示す。

長い計算は、受付時に計算番号を返す。計算番号は、1回の計算依頼の状態と結果を参照する識別子であり、共通の実行番号に対応付ける。呼び出し元は、計算の終了を待つか、進捗確認の操作で状態と結果を取得する。詳細な数式や長い履歴は保存し、必要な箇所を指定して取得できるようにする。

探索で得た候補は、共通の検証へ渡す。厳密な式への変換や検証が完了しなかった場合は、その段階までの結果を返す。数値誤差が小さいという情報は、数値候補の記録に含める。

<a name="design-verification"></a>

## 4. 検証結果の読み方

対応する上位項目：[3. 対象範囲](../01-requirements/requirements.ja.md#req-scope)、[7. 非機能要件と制約](../01-requirements/requirements.ja.md#req-quality)、[7.1 非機能要件](../01-requirements/requirements.ja.md#req-nonfunctional)、[8. 受入方針](../01-requirements/requirements.ja.md#req-acceptance)、[8.1 最初の受入範囲](../01-requirements/requirements.ja.md#req-initial-acceptance)、[N-01](../01-requirements/requirements.ja.md#req-n-01)、[N-02](../01-requirements/requirements.ja.md#req-n-02)、[受入確認：既知のLax接続](../01-requirements/requirements.ja.md#accept-known-lax)、[受入確認：未判定の扱い](../01-requirements/requirements.ja.md#accept-undecided)。

候補の検証では、次の3項目をそれぞれ判定する。

| 検査 | 確認する内容 | 結果に添える根拠 | 対応する上位項目 |
| --- | --- | --- | --- |
| <a name="check-curvature"></a>[零曲率条件](#check-curvature) | 運動方程式と模型の恒等式の下で、候補の曲率がスペクトルパラメータの許容範囲全体で零になるか | 曲率の計算と使用した条件。不成立なら消えない式 | [F-03](../01-requirements/requirements.ja.md#req-f-03) |
| <a name="check-equations"></a>[運動方程式全体の回収](#check-equations) | 零曲率条件と模型の恒等式から、対象模型の運動方程式全体が得られるか | 検査対象の全方程式と対応関係。不足がある場合は得られない方程式 | [F-04](../01-requirements/requirements.ja.md#req-f-04)、[受入確認：運動方程式を表さない候補](../01-requirements/requirements.ja.md#accept-missing-equations) |
| <a name="check-essential"></a>[スペクトルパラメータ依存の非自明性](#check-essential) | 許容する局所ゲージ変換によって、その依存を除去できないか | 許容する変換の範囲と除去できない根拠。除去可能なら具体的な変換 | [F-11](../01-requirements/requirements.ja.md#req-f-11)、[伝達事項：非自明性の検証条件](../01-requirements/requirements.ja.md#handoff-essential)、[受入確認：除去可能なスペクトルパラメータ依存](../01-requirements/requirements.ja.md#accept-removable-parameter) |

各項目の判定は、成立・不成立・未判定・未実施とする。3項目すべてが成立した候補だけを、指定した条件の下で検証済みのLax接続として表示する。1項目でも不成立なら要件を満たさない候補として示し、不成立はなくても未判定・未実施が残る場合は未検証とする。限られた形のゲージ変換を探して見つからなかったことだけでは、非自明性の成立としない。

計算の終了理由も別に返す。例えば時間切れなら、完了した検査の結果は保持し、着手したが判定を終えられなかった検査は未判定、未着手の検査は未実施とする。探索で候補が見つからなかったことは、探索範囲と終了理由として記録する。

<a name="design-workflow"></a>

## 5. 利用の流れと人の介入

対応する上位項目：[F-07](../01-requirements/requirements.ja.md#req-f-07)、[F-10](../01-requirements/requirements.ja.md#req-f-10)、[F-13](../01-requirements/requirements.ja.md#req-f-13)、[N-03](../01-requirements/requirements.ja.md#req-n-03)、[C-01](../01-requirements/requirements.ja.md#req-c-01)、[R-03](../01-requirements/requirements.ja.md#req-r-03)。

外部エージェントで探索する場合の流れは、次のとおりとする。

1. 研究者が模型、目的、守る制約、資源上限を示す。外部エージェントが利用可能なツールを確認し、模型と計算条件を登録する。具体的なansatzの次数や関数形は、エージェントに提案を依頼できる。
2. 模型の運動方程式を取得し、候補の検証または探索を依頼する。
3. 検証結果と根拠を読み、必要に応じて候補や探索条件を変更して次の計算を依頼する。
4. 目的の結果を得たとき、探索範囲を調べ終えたとき、または上限に達したときに終了し、結果と終了理由を取得する。

Pythonで使う研究者も、必要な操作を選んで同じ流れを実行できる。付属エージェントは、指定された範囲内でこの操作の選択と反復を行う。言語モデルによる解釈や説明は検証記録に対応付け、検証済みかどうかの表示は[第4章](#design-verification)の結果から決める。

研究者は途中経過を読み、停止後に条件を変更して再開できる。変更者、時点、内容、理由を記録し、介入前の結果を保持する。条件が変わった場合は、その変更がどの計算から適用されたかを示す。人が介入した実行は、研究評価で識別できるようにする。

再開では完了済みの結果を利用し、未完了の計算と残予算を確認する。通信の切断後に計算が継続したかどうかも確認する。上限を使い切った実行は、利用者が上限を変更して記録した場合に再開する。付属エージェントがGemini APIの無料枠に達した場合も、進捗を保存して停止する。

<a name="design-extensions"></a>

## 6. 計算ツールを追加する方法

対応する上位項目：[N-02](../01-requirements/requirements.ja.md#req-n-02)、[N-04](../01-requirements/requirements.ja.md#req-n-04)、[N-05](../01-requirements/requirements.ja.md#req-n-05)、[伝達事項：計算ツールの追加](../01-requirements/requirements.ja.md#handoff-tools)。

追加するツールには、計算処理と、その使い方を示す定義を用意する。定義には、名前と版、目的、入力・出力、対応する模型や条件、必要なソフトウェアを含める。登録後、利用者が有効にしたツールを共通のツール一覧に載せ、Python、MCP、付属エージェントから呼べるようにする。

例えば、新しい係数探索法を追加する場合は、模型と探索条件を受け取り、候補の式と成立を仮定した条件を返す処理を実装する。候補は[第4章](#design-verification)の検証へ渡し、その結果を保存する。既存ツールの計算処理を変更せず、追加した処理の入出力と利用例を単独で試験できる構成にする。

保存量の計算など、Lax候補の生成以外の解析も同じ方法で追加できる。その場合は、得られた量、その定義、適用条件、計算方法を結果に含める。必要なソフトウェアが未導入の場合は、ツール一覧に利用できない理由を示す。

<a name="design-next"></a>

## 7. 次に具体化する設計

対応する上位項目：[8.2 開発全体の受入れ](../01-requirements/requirements.ja.md#req-full-acceptance)、[8.3 研究成果の確認](../01-requirements/requirements.ja.md#req-research)、[9. 外部設計への伝達事項](../01-requirements/requirements.ja.md#req-handoff)、[N-06](../01-requirements/requirements.ja.md#req-n-06)、[C-02](../01-requirements/requirements.ja.md#req-c-02)、[R-01](../01-requirements/requirements.ja.md#req-r-01)、[R-02](../01-requirements/requirements.ja.md#req-r-02)、[伝達事項：動作環境と配布](../01-requirements/requirements.ja.md#handoff-distribution)、[伝達事項：研究評価](../01-requirements/requirements.ja.md#handoff-evaluation)。

[開発順序と移行条件](../01-requirements/requirements.ja.md#req-development)に従い、PCMの候補提案・計算・検証・再試行・報告を一続きに動かす範囲を具体化する。追加する設計対象は[ansatzの提案](../01-requirements/requirements.ja.md#req-f-14)、[探索失敗後の情報](../01-requirements/requirements.ja.md#req-f-15)、後続の[変形模型の提案](../01-requirements/requirements.ja.md#req-f-16)である。[エージェントの初期受入条件](../01-requirements/requirements.ja.md#accept-agent-loop)に対応する入力・出力と失敗時の例を先にそろえる。数式の入力と内部の計算表現の受け渡しを明記し、[入力の既存案](../03-internal-design/model-input.ja.md#detail-scope)を見直す。3検査については、同書の[後続設計への引継ぎ](../03-internal-design/model-input.ja.md#detail-handoff)に従って処理と根拠を具体化する。

初期版に必要な入出力、実行管理、接続、判定手順を確認した範囲から実装する。後続の対応模型、探索方法、配布と研究評価は段階的に具体化する。[要件定義書第9章](../01-requirements/requirements.ja.md#req-handoff)の伝達事項は、対応する設計で具体化し、要件番号と確認例を添える。最初の動作確認の範囲は、[要件定義書第8.1節](../01-requirements/requirements.ja.md#req-initial-acceptance)に従う。

<a name="design-pcm-implementation"></a>

## 8. PCMの初期実装

参照元：[起動手順](../../README.md#quickstart)。上位項目：[最初の受入範囲](../01-requirements/requirements.ja.md#req-initial-acceptance)。内部設計：[検証処理と実行管理](../03-internal-design/pcm-verification.ja.md#verification-scope)。

利用者はPCMの作用の係数を数式で与え、目的を文章で指定する。Pythonの `pcm_model`、TOMLの `model.action_prefactor` は同じ入力を組み立てる。群、カレントの定義、領域は[入力設計の規約](../03-internal-design/model-input.ja.md#conventions-model)を使い、完全な定義を結果に保存する。別の作用をPCMとして計算することはせず、未対応として返す。

| 経路 | 入力と操作 | 得る結果 |
| --- | --- | --- |
| <a name="pcm-use-python"></a>[Python](#pcm-use-python) | `derive_equations`、`verify_candidate`、`solve_scalar_ansatz` | 辞書形式の数式、3検査の判定、根拠、適用範囲 |
| <a name="pcm-use-mcp"></a>[MCP](#pcm-use-mcp) | `available_calculations` でスキーマを取得し、`pcm_equations`、`pcm_verify`、`pcm_verify_scalar`、`pcm_solve_scalar` の `arguments` に入力を渡す | 時間制限つき計算の結果。外部エージェントが反復と記録を管理する |
| <a name="pcm-use-agent"></a>[付属エージェント](#pcm-use-agent) | `nlsm-lax agent` にTOMLを渡す | LangGraphによる提案・計算・再提案、SQLiteの履歴、終了理由、JSON出力 |

付属エージェントが提案できる範囲は、現在登録された計算ツールの入力範囲である。初期版では有理関数の形と未定係数を変えて試す。場の高次の冪や非多項式の場依存を一般的に生成する機能は未実装で、対応範囲外の候補を検証済みにしない。

検証済みは3検査の成立を表す。判定できない非自明性は未判定、計算の時間切れは計算終了理由として返す。未定係数の求解から解が返らない場合も、指定したansatzで候補が得られなかったという結果に留める。エージェントの終了時の提案は未検証の提案として保存する。

実装済みの受入確認は、既知PCM、零接続、カレント自身、除去可能なゲージ依存、未判定の扱い、保存と再検算、固定提案による再試行である。MCPの実通信とLiteLLMの模擬HTTP通信も確認する。実モデルの探索性能、研究対象への拡大、機械学習探索、公開配布、研究評価は未完了である。
