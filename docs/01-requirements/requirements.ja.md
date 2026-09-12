# 要件定義書

対象：nlsm-lax-agent。更新日：2026年9月12日。状態：ヒアリング結果と初期版の到達点を整理した草案。本体は未実装。

本書は、利用目的、対象範囲、システムに求める振る舞い、受入条件を定める。外部設計では、利用者から見た操作・入出力・利用条件を定める。内部設計では、それを支える構成と各部分の役割、データ構造、数式の規約と処理手順を具体化する。文書を確認する順序は[文書一覧と参照の方針](../../README.md#documentation)に従う。

<a name="req-purpose"></a>

## 1. 背景と目的

対応する設計：[1. 提供するものと利用方法](../02-external-design/external-design.ja.md#design-usage)。内訳：[現在の作業と課題](#req-as-is)、[期待する成果と役割分担](#req-to-be)。

2次元非線形シグマ模型の可積分性を調べる研究では、Lax接続の候補生成、記号計算、検証、候補の修正を繰り返す。本システムは、この作業を研究者とエージェントが実行するための計算機能を提供する。

目的は、指定した模型について、運動方程式を表し、非自明なスペクトルパラメータ依存を持つLax接続を探索・検証し、結果を第三者が再検算できる形で残すことである。研究上は、有限個の結合定数を持つ模型族についてLax接続の成立条件を解析し、比較実験で探索・検証の改善を示す。再利用できるソフトウェアと、研究結果の再検算に必要な資料を公開する。

<a name="req-as-is"></a>

### 1.1 現在の作業と課題（As-Is）

参照元：[背景と目的](#req-purpose)、[利用場面](#req-users)、[文書一覧](../../README.md#documentation)。対応する要求：[ansatzの提案](#req-f-14)、[探索失敗後の情報](#req-f-15)。

研究者は、数式で模型を定義するか文献から持ってきて、運動方程式を準備する。文献・経験・勘から未定係数を含むLax接続のansatzを導入し、曲率と運動方程式を比較する。係数の条件を解き、スペクトルパラメータとなる自由度を調べ、適切な候補が得られなければansatzの選択に戻る。

確認された主な負担は、場やその微分の冪をどこまで含めるか、多項式やさらに非線形な関数形をどう選ぶかという判断である。変形模型の設計も支援対象として希望されているが、利用者の実務経験は少ないため、その具体的な作業の整理は文献に基づく仮説として扱う。

<a name="req-to-be"></a>

### 1.2 期待する成果と役割分担（To-Be）

参照元：[背景と目的](#req-purpose)、[利用場面](#req-users)、[文書一覧](../../README.md#documentation)。対応する要求：[結果の吟味と方向変更](#req-f-13)、[ansatzの提案](#req-f-14)、[探索失敗後の情報](#req-f-15)、[変形模型の提案](#req-f-16)。

期待する成果は、変形模型やLax接続の具体的な関数形を、検証済み、または容易に検証できる情報とともに得ることである。検証が完了した範囲と未完了の範囲を明示し、[検証済みの採用条件](#req-scope)に従う。候補が得られなかった場合にも、別のansatzの立て方、No-Goと結論するために必要な条件・検査、現在までに排除できた範囲を得られることを求める。

研究者は主に結果を吟味し、探索を方向づける。エージェントは、与えられた目的・制約・資源上限の下で候補の提案、計算、検証、修正を進める。個々の候補の次数や関数形を研究者がすべて事前に決定することを、利用の前提にしない。研究者が示した方向変更は、その後の探索に反映して記録する。

初期の研究対象候補は、T¹,¹を標的空間とする模型、Arutyunov–Bassi–Lacroix（ABL）模型、主カイラル模型（PCM）を出発点とする新しい変形である。対象は作用とパラメータ条件まで特定する。利用者が用意する模型情報は数式であり、具体的な入力形式は[外部設計への伝達事項](#req-handoff)として扱う。

変形の設計支援については、出発点の模型や保つ性質から適用できる構成方法を調べ、変形作用とLax接続の候補を検証に結び付けることを仮説とする。作用から係数条件を求める例は[Hoare, §3–4](https://arxiv.org/abs/2109.14284)、幾何学的な構成から作用とLax接続を導く例は[Lacroix–Wallberg, §5](https://arxiv.org/abs/2311.09301)、補助場を使って相互作用を選ぶ例は[Ferko–Smith](https://arxiv.org/abs/2405.05899)を参照する。これらの構成方法の全実装を初期版の条件にはしない。

<a name="req-users"></a>

## 2. 利用者と利用場面

対応する設計：[1. 提供するものと利用方法](../02-external-design/external-design.ja.md#design-usage)。

主な利用者は、研究対象と目的を指定して結果を吟味・方向づける研究者、および保存された結果を再検算する研究者である。[現在の作業と課題](#req-as-is)と[期待する成果](#req-to-be)から、利用場面を次のように整理する。

| 利用場面 | 利用者が得たい成果と価値 | 対応する要求 |
| --- | --- | --- |
| <a name="story-lax"></a>[与えた模型のLax接続を探す](#story-lax) | 数式で与えた模型に対して、ansatzの提案・修正と検証を任せ、具体的な接続と根拠を得て物理的な分析へ進む | [F-14](#req-f-14)、[F-03](#req-f-03)、[F-04](#req-f-04)、[F-11](#req-f-11) |
| <a name="story-deformation"></a>[変形模型を探す](#story-deformation) | 出発点の模型と目的を与え、変形作用とLax接続の候補を検証に必要な情報とともに得る | [F-16](#req-f-16)、[F-12](#req-f-12) |
| <a name="story-negative"></a>[探索の続行方針を決める](#story-negative) | 候補が得られない場合にも、別のansatzや排除できた範囲・必要な検査を知り、次の方向を決める | [F-15](#req-f-15)、[F-13](#req-f-13)、[N-01](#req-n-01) |

これらの作業を利用する経路は次のとおりとする。

| 利用場面 | 利用者の操作 | システムから得る結果 | 対応する設計 |
| --- | --- | --- | --- |
| <a name="user-python"></a>[手動で計算する](#user-python) | Pythonから必要な計算を呼び出す | 指定した計算の結果と根拠 | [Pythonから使う](../02-external-design/external-design.ja.md#use-python) |
| <a name="user-external"></a>[外部エージェントに計算を依頼する](#user-external) | CodexやClaude Codeなどに対象と目的を伝える | エージェントが呼び出した探索・検証の結果 | [外部エージェントから使う](../02-external-design/external-design.ja.md#use-external) |
| <a name="user-agent"></a>[付属エージェントで探索する](#user-agent) | 模型、探索範囲、実行上限を指定する | 探索履歴、候補、検証結果、終了理由 | [付属エージェントから使う](../02-external-design/external-design.ja.md#use-agent) |

いずれの場合も、研究の目的と結果の物理的な解釈は研究者が担う。目的に沿った模型・ansatzの候補の提案は、エージェントに依頼できる。

<a name="req-scope"></a>

## 3. 対象範囲

対応する設計：[4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)。

対象機能は、模型と候補の入力、記号計算と機械学習による候補探索、結合定数についてのLax接続の存在条件の探索、候補の検証、途中経過の確認と条件変更、計算の中断・再開、結果の保存・再検算とする。計算ツールを後から追加できることも対象範囲に含める。

物理的な必須の検査は、指定した模型・領域・仮定の下での、零曲率条件と運動方程式の対応、およびスペクトルパラメータ依存の非自明性とする。保存量の独立性・Poisson可換性、一般的な非可積分性の自動証明は、本書の受入対象に含めない。探索失敗後にも、[F-15](#req-f-15)に従い、代替案とNo-Goを判断するための情報を返す。

スペクトルパラメータは、時空に依存せず、場や模型の結合定数から独立した補助パラメータを指す。本書でいう非自明性は、運動方程式と模型の恒等式の下でも、許容する局所ゲージ変換によって、その依存を除去できないこととする。局所ゲージ変換は、時空座標、場とその有限階の微分、スペクトルパラメータの関数として与えられ、対象領域で正則かつ可逆なものを扱う。境界条件を課す場合は、その保存も要求する。パラメータに依存するゲージ変換で見かけ上の依存を導入できるため、式にパラメータが現れることだけでは非自明性の根拠にならない。[M. Marvan, *On the spectral parameter problem*, arXiv:0804.2031](https://arxiv.org/abs/0804.2031)

本システムが検証済みのLax接続として採用するには、[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)のすべてで成立を確認することを必須とする。非自明性が未判定・未実施の候補は、未検証の候補として保存する。

最初に受け入れる範囲と研究成果の確認条件は[要件定義書第8章](#req-acceptance)に定める。具体的な対応模型、操作、入出力などの外部設計への伝達事項は、[要件定義書第9章](#req-handoff)にまとめる。

<a name="req-functions"></a>

## 4. 機能要件

対応する設計：[3. 呼び出せる操作](../02-external-design/external-design.ja.md#design-operations)。

要件は番号で識別し、後続の設計・試験から参照する。Fは機能、Iは外部接続、Nは非機能、Cは開発上の制約、Rは研究成果を表す。[要件定義書第4章](#req-functions)・[要件定義書第5章](#req-data)・[要件定義書第6章](#req-interfaces)・[要件定義書第7章](#req-quality)は開発全体に対する要求であり、受入条件は実装後に確認する条件を示す。研究成果の確認条件は[要件定義書第8.3節](#req-research)に定める。

| 番号 | 要求内容 | 受入条件 | 対応する設計 |
| --- | --- | --- | --- |
| <a name="req-f-01"></a>[F-01](#req-f-01) | 利用者は、作用、場、結合定数、適用領域と仮定を指定し、対応する運動方程式を取得できること。 | 主カイラル模型の入力から、基準となる運動方程式が得られる。入力の不足や未対応の形式は、理由とともに通知される。 | [模型](../02-external-design/external-design.ja.md#input-model)、[模型と計算条件を登録する](../02-external-design/external-design.ja.md#operation-register)、[運動方程式を導出する](../02-external-design/external-design.ja.md#operation-equations)、[模型入力の詳細](../03-internal-design/model-input.ja.md#detail-model)、[入力検査の手順](../03-internal-design/model-input.ja.md#detail-validation) |
| <a name="req-f-02"></a>[F-02](#req-f-02) | 利用者が用意したLax接続の候補を、対象模型と対応付けて検証に渡せること。 | 探索を実行せずに既知の候補を検証でき、結果から入力模型と候補を特定できる。 | [候補の接続](../02-external-design/external-design.ja.md#input-candidate)、[候補を検証する](../02-external-design/external-design.ja.md#operation-verify)、[候補入力の詳細](../03-internal-design/model-input.ja.md#detail-candidate)、[入力検査の手順](../03-internal-design/model-input.ja.md#detail-validation) |
| <a name="req-f-03"></a>[F-03](#req-f-03) | 運動方程式と模型の恒等式が成立するとき、候補の曲率がスペクトルパラメータの許容範囲全体で零になるかを検査できること。 | 既知の正しい候補では成立が確認される。不成立の場合は消えない式を、判定できない場合は未解決の計算を示す。 | [候補を検証する](../02-external-design/external-design.ja.md#operation-verify)、[零曲率条件](../02-external-design/external-design.ja.md#check-curvature) |
| <a name="req-f-04"></a>[F-04](#req-f-04) | スペクトルパラメータ依存を含む零曲率条件と模型の恒等式から、対象模型の運動方程式全体が得られるかを検査できること。 | 既知の正しい候補と、運動方程式を全く、または一部しか表さない候補を区別できる。検査対象の運動方程式を結果に示す。 | [候補を検証する](../02-external-design/external-design.ja.md#operation-verify)、[運動方程式全体の回収](../02-external-design/external-design.ja.md#check-equations) |
| <a name="req-f-05"></a>[F-05](#req-f-05) | 指定した模型と候補の式の形・探索範囲に対して、記号計算で候補を探索できること。 | 既知の候補を含む基準課題で候補が得られ、[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)に渡される。見つからない場合も探索範囲と終了理由を返す。 | [探索条件](../02-external-design/external-design.ja.md#input-search)、[記号計算で候補を探す](../02-external-design/external-design.ja.md#operation-symbolic) |
| <a name="req-f-06"></a>[F-06](#req-f-06) | 機械学習によって候補を生成し、厳密な数式へ変換できた候補を[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)で検証できること。 | 基準課題で生成から検証まで実行できる。数式への変換に失敗した候補や数値的な誤差だけが小さい候補は、未検証として残る。 | [探索条件](../02-external-design/external-design.ja.md#input-search)、[機械学習で候補を探す](../02-external-design/external-design.ja.md#operation-ml) |
| <a name="req-f-07"></a>[F-07](#req-f-07) | 検証結果を参照して候補や探索範囲を変更し、再探索できること。 | 失敗した探索の結果を参照して次の探索を実行でき、変更前後の条件と結果が履歴に残る。 | [5. 利用の流れと人の介入](../02-external-design/external-design.ja.md#design-workflow)、[停止・条件変更・再開を行う](../02-external-design/external-design.ja.md#operation-control) |
| <a name="req-f-08"></a>[F-08](#req-f-08) | [要件定義書第5章](#req-data)の情報を保存できること。 | 計算終了後に保存内容を読み出せ、入力から結果までの対応を確認できる。 | [2. 入力と計算の記録](../02-external-design/external-design.ja.md#design-inputs)、[模型と計算条件を登録する](../02-external-design/external-design.ja.md#operation-register)、[進捗や結果を読む](../02-external-design/external-design.ja.md#operation-results)、[記録を出力・再検算する](../02-external-design/external-design.ja.md#operation-records)、[入力結果と保存への引渡し](../03-internal-design/model-input.ja.md#validation-result) |
| <a name="req-f-09"></a>[F-09](#req-f-09) | 保存した入力と候補を使い、言語モデルを呼ばずに再検算できること。 | 保存した実行条件を再現した環境で、検証結果と成立条件が一致する。 | [記録を出力・再検算する](../02-external-design/external-design.ja.md#operation-records)、[数式の読み取りと正規化](../03-internal-design/model-input.ja.md#detail-expressions) |
| <a name="req-f-10"></a>[F-10](#req-f-10) | 実行を中断し、保存済みの進捗から再開できること。 | 利用者による中断後に再開でき、完了済みの結果と未完了の計算を区別できる。上限到達後は、利用者が上限を変更した場合に再開でき、その変更が履歴に残る。 | [5. 利用の流れと人の介入](../02-external-design/external-design.ja.md#design-workflow)、[停止・条件変更・再開を行う](../02-external-design/external-design.ja.md#operation-control) |
| <a name="req-f-11"></a>[F-11](#req-f-11) | スペクトルパラメータ依存の非自明性を、許容ゲージ変換の範囲と根拠を明示して検査できること。 | 受入対象の既知のLax接続で、依存を除去できない根拠を示せる。除去可能と判定した場合は、それを示す変換を返す。変換の探索に失敗しただけの場合は未判定とし、探索時に仮定した変換の形の範囲だけで除去できないことを、非自明性の成立根拠にしない。 | [候補の接続](../02-external-design/external-design.ja.md#input-candidate)、[候補を検証する](../02-external-design/external-design.ja.md#operation-verify)、[スペクトルパラメータ依存の非自明性](../02-external-design/external-design.ja.md#check-essential)、[局所ゲージ変換の規約](../03-internal-design/model-input.ja.md#conventions-gauge) |
| <a name="req-f-12"></a>[F-12](#req-f-12) | 有限個の結合定数を持つ模型族と探索範囲を指定し、Lax接続の候補と、その接続が3検査を満たす結合定数の条件を求められること。 | 既知の成立条件を含む基準課題で、その条件に対応する候補を得る。検証済みとする範囲では[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)が成立し、未解決・未探索の範囲を区別して示す。探索した候補の式の形と範囲も残す。 | [探索条件](../02-external-design/external-design.ja.md#input-search)、[Lax接続の存在条件を結合定数について求める](../02-external-design/external-design.ja.md#operation-couplings) |
| <a name="req-f-13"></a>[F-13](#req-f-13) | 利用者は、実行の途中経過を確認し、必要に応じて停止、探索条件の変更、再開を行えること。 | 進捗、現在の条件、候補、検証結果を確認できる。変更者、時点、変更前後の条件、理由を記録し、介入前の結果を保持する。変更後の結果を、それが得られた条件に対応付けられる。 | [5. 利用の流れと人の介入](../02-external-design/external-design.ja.md#design-workflow)、[進捗や結果を読む](../02-external-design/external-design.ja.md#operation-results)、[停止・条件変更・再開を行う](../02-external-design/external-design.ja.md#operation-control) |
| <a name="req-f-14"></a>[F-14](#req-f-14) | 模型と研究目的に対して、場やその微分への依存の次数・関数形を含むLax接続のansatzを提案し、検証結果を受けて修正できること。 | 記号計算に渡せる候補と選択理由を返し、基準課題で不成立の結果を参照した別候補への再試行を記録する。提案だけで検証済みとは扱わない。 | [外部設計で具体化](../02-external-design/external-design.ja.md#design-next)。要求の根拠：[現在の課題](#req-as-is)、[期待する成果](#req-to-be)、[Lax探索の利用場面](#story-lax) |
| <a name="req-f-15"></a>[F-15](#req-f-15) | 候補が得られない場合、試したansatz・仮定・未解決の計算を示し、別の立て方とNo-Goを判断するための条件・検査を提示できること。 | 対象を限定した不存在を証明した結果と、求解失敗・時間切れ・未探索を区別する。不存在の主張には範囲と根拠を添え、代替案や文献に基づく提案は未検証と明示する。 | [外部設計で具体化](../02-external-design/external-design.ja.md#design-next)。要求の根拠：[現在の課題](#req-as-is)、[期待する成果](#req-to-be)、[続行判断の利用場面](#story-negative) |
| <a name="req-f-16"></a>[F-16](#req-f-16) | 出発点の模型と研究目的に対して、変形後の作用とLax接続の候補を提案し、その仮定・パラメータ条件・検証状況を示せること。 | 対応を公表する構成方法の基準課題で、元の模型との関係を示す作用と候補を返し、[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)へ渡す。既知模型との関係と新規性の未確認部分を明記する。 | [外部設計で具体化](../02-external-design/external-design.ja.md#design-next)。要求の根拠：[期待する成果と文献に基づく仮説](#req-to-be)、[変形探索の利用場面](#story-deformation) |

<a name="req-data"></a>

## 5. データ要件

対応する設計：[2. 入力と計算の記録](../02-external-design/external-design.ja.md#design-inputs)。

[F-08](#req-f-08)で保存する情報の最小範囲を以下に定める。保存形式は内部設計で定める。

| 情報 | 保存する内容 | 対応する設計 |
| --- | --- | --- |
| <a name="data-input"></a>[入力](#data-input) | 模型、作用、場、結合定数、領域、仮定、検査対象の運動方程式、候補の数式、スペクトルパラメータとその領域、補助線形問題のゲージ群と許容ゲージ変換の条件 | [模型](../02-external-design/external-design.ja.md#input-model)、[候補の接続](../02-external-design/external-design.ja.md#input-candidate)、[候補入力の詳細](../03-internal-design/model-input.ja.md#detail-candidate)、[数式の読み取りと正規化](../03-internal-design/model-input.ja.md#detail-expressions)、[入力結果と保存への引渡し](../03-internal-design/model-input.ja.md#validation-result) |
| <a name="data-history"></a>[実行条件と履歴](#data-history) | 使用したソフトウェアの版、計算方法と設定、使用した場合の言語モデル・プロンプト・入出力・乱数の設定、計算手順、各ツールの入出力、候補や条件の変更、中断・終了理由 | [進捗や結果を読む](../02-external-design/external-design.ja.md#operation-results) |
| <a name="data-verification"></a>[検証結果](#data-verification) | 入力との対応、検査した性質ごとの判定、成立条件、根拠となる数式、スペクトルパラメータ依存を除去できる変換または除去できない根拠、未解決・未実施の検査 | [候補を検証する](../02-external-design/external-design.ja.md#operation-verify) |
| <a name="data-family"></a>[模型族の探索結果](#data-family) | 結合定数の探索範囲、得られた候補と成立条件、検証済み・未解決・未探索の範囲、探索した候補の式の形 | [Lax接続の存在条件を結合定数について求める](../02-external-design/external-design.ja.md#operation-couplings) |
| <a name="data-intervention"></a>[人の介入](#data-intervention) | 介入の有無、変更者、時点、対象、変更前後の条件、理由、作業時間。作業時間を測っていない場合は未計測と記録する | [停止・条件変更・再開を行う](../02-external-design/external-design.ja.md#operation-control) |
| <a name="data-resources"></a>[使用資源と費用](#data-resources) | 実行環境、設定した上限、分岐・再試行・再開を含む経過時間と計算時間、最大メモリ使用量、使用した場合のGPU・言語モデルの利用量とAPI料金。実測値・推定値・取得できない値を区別する | [実行条件](../02-external-design/external-design.ja.md#input-execution) |

外部エージェント自身のモデル設定・入出力・使用資源は、取得できる範囲で記録し、取得できない項目は不明とする。本システムが受け取ったツール入力、実行した計算、その結果は、利用経路によらず保存する。

<a name="req-interfaces"></a>

## 6. 外部インターフェース要件

対応する設計：[1. 提供するものと利用方法](../02-external-design/external-design.ja.md#design-usage)、[3. 呼び出せる操作](../02-external-design/external-design.ja.md#design-operations)。

MCP（Model Context Protocol）は、外部エージェントがツールを呼び出すための通信規約を指す。

| 番号 | 要求内容 | 受入条件 | 対応する設計 |
| --- | --- | --- | --- |
| <a name="req-i-01"></a>[I-01](#req-i-01) | Pythonから各計算機能を直接利用できること。 | 付属エージェントを起動せず、候補の探索・検証・再検算を実行できる。 | [Pythonから使う](../02-external-design/external-design.ja.md#use-python) |
| <a name="req-i-02"></a>[I-02](#req-i-02) | 外部エージェントからMCPを通じて各計算機能を利用できること。 | 付属エージェントとその言語モデルの設定がない環境で、MCPクライアントから探索・検証・再検算を呼び出せる。 | [外部エージェントから使う](../02-external-design/external-design.ja.md#use-external) |
| <a name="req-i-03"></a>[I-03](#req-i-03) | 付属エージェントが、指定された範囲内で計算を選択して探索を進められること。 | 基準課題で、候補生成、検証結果を受けた修正、終了まで実行できる。言語モデルの接続先を変更しても物理計算の変更を要しない。 | [付属エージェントから使う](../02-external-design/external-design.ja.md#use-agent) |

<a name="req-quality"></a>

## 7. 非機能要件と制約

対応する設計：[4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)。

<a name="req-nonfunctional"></a>

### 7.1 非機能要件

対応する設計：[4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)。

| 番号 | 要求内容 | 受入条件 | 対応する設計 |
| --- | --- | --- | --- |
| <a name="req-n-01"></a>[N-01](#req-n-01) | 検査の成立、不成立、未判定、未実施を区別して返すこと。 | 判定できない計算や時間切れを成立・不成立に含めない。[F-03](#req-f-03)・[F-04](#req-f-04)が成立しても[F-11](#req-f-11)が未判定・未実施なら、検証済みとして採用しない。探索失敗を根拠とした非可積分性の判定を返さない。 | [4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)、[入力検査の手順](../03-internal-design/model-input.ja.md#detail-validation) |
| <a name="req-n-02"></a>[N-02](#req-n-02) | 利用経路によらず同じ物理計算と検証基準を適用すること。 | 同じ模型・候補・仮定・ソフトウェアの版を使い、Python、MCP、付属エージェント経由の検証結果と成立条件が一致する。 | [4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)、[6. 計算ツールを追加する方法](../02-external-design/external-design.ja.md#design-extensions) |
| <a name="req-n-03"></a>[N-03](#req-n-03) | 本システムが管理する実行について、時間・メモリの上限と、言語モデルを呼ぶ場合の利用・費用上限を、条件分岐・再試行・再開を含めて適用すること。 | 分岐や再開によって消費済みの予算が帳消しにならず、上限到達時に停止理由と保存済みの進捗を返す。外部エージェント自身が消費する資源は管理対象に含めず、取得できない利用量・料金は不明と記録する。計測方法と停止までの許容時間は[要件定義書第9章](#req-handoff)で具体化する。 | [2. 入力と計算の記録](../02-external-design/external-design.ja.md#design-inputs)、[5. 利用の流れと人の介入](../02-external-design/external-design.ja.md#design-workflow)、[実行条件](../02-external-design/external-design.ja.md#input-execution) |
| <a name="req-n-04"></a>[N-04](#req-n-04) | 機械学習機能を追加導入でき、検証と記号計算による探索を単独でも利用できること。 | 機械学習用の依存ソフトウェアがない環境で、記号計算による探索・検証・再検算が動作する。 | [6. 計算ツールを追加する方法](../02-external-design/external-design.ja.md#design-extensions)、[利用できるツールを調べる](../02-external-design/external-design.ja.md#operation-tools)、[機械学習で候補を探す](../02-external-design/external-design.ja.md#operation-ml) |
| <a name="req-n-05"></a>[N-05](#req-n-05) | 利用者が、公開された追加手順に従い、新しい探索方法、物理解析、外部の研究コードや数式処理ソフトウェアを計算ツールとして追加できること。 | ツールの実装・入出力の定義・登録を追加した例が、Python、MCP、付属エージェントから利用できる。既存ツールの計算処理を変更せず、追加ツールを単独で実行・試験できる。新しい探索ツールが返すLax接続の候補にも[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)を適用する。 | [6. 計算ツールを追加する方法](../02-external-design/external-design.ja.md#design-extensions)、[利用できるツールを調べる](../02-external-design/external-design.ja.md#operation-tools) |
| <a name="req-n-06"></a>[N-06](#req-n-06) | ソースコード、利用・改変・再配布の条件を明記したライセンス、版を指定して導入できるPythonパッケージ、導入手順、Python利用例、MCP接続例を公開すること。 | 対応する新規環境で、配布物と手順を用いて導入し、標準の再検算とMCP経由の計算を実行できる。配布物の版と対応するソースコードを特定できる。 | [具体化予定](../02-external-design/external-design.ja.md#design-next) |

<a name="req-constraints"></a>

### 7.2 開発上の制約

対応する設計：[1. 提供するものと利用方法](../02-external-design/external-design.ja.md#design-usage)。

| 番号 | 制約 | 確認方法 | 対応する設計 |
| --- | --- | --- | --- |
| <a name="req-c-01"></a>[C-01](#req-c-01) | 付属エージェントの開発・動作確認は、Gemini APIの無料枠とローカルで動かす言語モデルで実施できること。 | 両方の接続先で[I-03](#req-i-03)を確認する。無料枠の利用上限では進捗を保存して停止し、有料の接続先へ自動で切り替わらないことを確認する。 | [5. 利用の流れと人の介入](../02-external-design/external-design.ja.md#design-workflow)、[付属エージェントから使う](../02-external-design/external-design.ja.md#use-agent) |
| <a name="req-c-02"></a>[C-02](#req-c-02) | 初期の対応環境をLinuxとWSL2上のLinuxとし、標準の記号計算・検証・再検算はCPUのみで、商用の数式処理ソフトウェアを必要とせず実行できること。 | 両環境で公表した手順に従い、標準の記号計算・検証・再検算が動作する。Pythonの対応版と必要資源を示し、機械学習・ローカル言語モデル・外部ソフトウェアを使う機能の追加条件を区別して記載する。 | [具体化予定](../02-external-design/external-design.ja.md#design-next) |

<a name="req-acceptance"></a>

## 8. 受入方針

対応する設計：[4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)。

<a name="req-initial-acceptance"></a>

### 8.1 最初の受入範囲

参照元：[文書一覧](../../README.md#documentation)。

入力の内部設計：[入力詳細の対象と処理](../03-internal-design/model-input.ja.md#detail-scope)。

対応する設計：[4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)、[7. 次に具体化する設計](../02-external-design/external-design.ja.md#design-next)。

最初の実装はSU(2)主カイラル模型を基準課題とし、数式による模型指定から、付属エージェントによるansatzの提案、記号計算・検証、失敗に応じた再提案、結果の保存・再検算までを一続きに動かす。同じ計算ツールをPythonとMCPから利用できることも含む。次の全項目を満たしたとき、この範囲を受け入れる。これは[開発順序](#req-development)の最初の到達点である。

| 確認すること | 対応要件 | 対応する設計 |
| --- | --- | --- |
| <a name="accept-known-lax"></a>既知の作用から運動方程式を取得し、既知のLax接続について零曲率条件、運動方程式全体の回収、スペクトルパラメータ依存の非自明性がすべて成立する | [F-01](#req-f-01)、[F-02](#req-f-02)、[F-03](#req-f-03)、[F-04](#req-f-04)、[F-11](#req-f-11)、[I-01](#req-i-01) | [4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification)、[入力・方程式・候補の確認例](../03-internal-design/model-input.ja.md#detail-cases) |
| <a name="accept-missing-equations"></a>零接続と、模型の恒等式だけで平坦になる接続について、[F-03](#req-f-03)の成立と[F-04](#req-f-04)の不成立を区別する | [F-03](#req-f-03)、[F-04](#req-f-04)、[N-01](#req-n-01) | [運動方程式全体の回収](../02-external-design/external-design.ja.md#check-equations)、[入力・方程式・候補の確認例](../03-internal-design/model-input.ja.md#detail-cases) |
| <a name="accept-removable-parameter"></a>パラメータに依存しない接続と、そこにゲージ変換で見かけ上の依存を付けた接続を、非自明性の要件を満たさない候補として識別する | [F-11](#req-f-11)、[N-01](#req-n-01) | [スペクトルパラメータ依存の非自明性](../02-external-design/external-design.ja.md#check-essential)、[入力・方程式・候補の確認例](../03-internal-design/model-input.ja.md#detail-cases) |
| <a name="accept-undecided"></a>非自明性の判定が完了する前に検査を中断した候補について、未判定を返し、検証済みとして採用しない | [F-11](#req-f-11)、[N-01](#req-n-01) | [4. 検証結果の読み方](../02-external-design/external-design.ja.md#design-verification) |
| <a name="accept-recheck"></a>検証記録を保存し、言語モデルと機械学習機能を使わずに再検算して同じ結果を得る | [F-08](#req-f-08)、[F-09](#req-f-09)、[I-01](#req-i-01)、[N-04](#req-n-04)の検証・再検算に関する部分 | [記録を出力・再検算する](../02-external-design/external-design.ja.md#operation-records)、[入力・方程式・候補の確認例](../03-internal-design/model-input.ja.md#detail-cases) |
| <a name="accept-agent-loop"></a>付属エージェントが不成立の候補の検証結果を受けて別のansatzを提案し、再計算・結果報告まで進める。同じ計算をPythonとMCPから実行でき、無料API枠またはローカル言語モデルで実際の接続を確認する | [F-07](#req-f-07)、[F-14](#req-f-14)、[F-15](#req-f-15)、[I-01](#req-i-01)、[I-02](#req-i-02)、[I-03](#req-i-03)、[C-01](#req-c-01)の初期動作範囲 | [初期版の設計](../02-external-design/external-design.ja.md#design-next) |

<a name="req-full-acceptance"></a>

### 8.2 開発全体の受入れ

対応する設計：[7. 次に具体化する設計](../02-external-design/external-design.ja.md#design-next)。

[要件定義書第8.1節](#req-initial-acceptance)で付属エージェントと共通ツールの最初の動作を受け入れた後、対応模型・探索方法・接続先の拡大、ツールの追加、配布などを段階的に受け入れる。開発全体の受入れでは、[要件定義書第4章](#req-functions)・[要件定義書第5章](#req-data)・[要件定義書第6章](#req-interfaces)・[要件定義書第7章](#req-quality)の全要件について確認結果を残す。基準課題の具体的な入力・期待結果・実行環境は試験計画で定める。

<a name="req-research"></a>

### 8.3 研究成果の確認

対応する設計：[7. 次に具体化する設計](../02-external-design/external-design.ja.md#design-next)。

論文に向けた到達点は、公開して再利用できるツール、比較による改善の実証、模型族についての解析結果をそろえることとする。[N-06](#req-n-06)に加え、次の全項目を研究成果の確認条件とする。

| 番号 | 要求内容 | 確認条件 | 対応する設計 |
| --- | --- | --- | --- |
| <a name="req-r-01"></a>[R-01](#req-r-01) | 有限個の結合定数を持つ模型族を少なくとも1つ解析し、Lax接続とその成立条件を根拠付きで提示すること。 | [F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)を満たす結果について、既知の分類との対応、得られた成立条件、未解決・未探索の範囲を示す。主要結果に独立した導出または別実装による検算を添え、新規性を主張する場合は既知結果や同値変換との照合を示す。 | [具体化予定](../02-external-design/external-design.ja.md#design-next) |
| <a name="req-r-02"></a>[R-02](#req-r-02) | 物理解析に対する探索・検証ツールの改善効果を、比較実験で示すこと。 | 共通の入力・探索範囲・最終検証基準・資源上限で、言語モデルを使わない探索、同じ外部エージェントでの本ツール群の有無、同じ言語モデルでの独立提案と反復探索を比較する。事前に定めた指標で、誤採用、探索できる範囲、成功率、使用資源などの改善と適用範囲を示す。機械学習探索の効果を主張する場合は、言語モデルを使わない機械学習探索も比較に含める。 | [具体化予定](../02-external-design/external-design.ja.md#design-next) |
| <a name="req-r-03"></a>[R-03](#req-r-03) | 調整に使わない課題で反復評価し、第三者が主要結果を再検算・再集計できる資料を公開すること。 | 評価前に課題・試行数・成功条件・集計方法を固定する。失敗・中断を含む全試行、誤採用、時間・メモリ・費用、ばらつき、人の介入を記録する。論文に用いた入力、候補、検証結果、実行履歴、環境の版、再検算と集計の手順・コードを公開し、それらから表・図の集計を再現できる。 | [5. 利用の流れと人の介入](../02-external-design/external-design.ja.md#design-workflow)、[記録を出力・再検算する](../02-external-design/external-design.ja.md#operation-records) |

独立提案は、先行する候補の失敗や検証結果を次の提案に返さない生成方式を指す。探索成功は、予算内に[F-03](#req-f-03)・[F-04](#req-f-04)・[F-11](#req-f-11)を満たす候補を得たこととし、成功率の分母には開始した全試行を含める。介入した試行と介入なしの試行は分けて集計する。比較中も最終検証基準は共通とし、評価用の正解・検算資料を探索側に渡さない。同じ模型の座標・基底の変更を、独立した模型として数えない。

<a name="req-development"></a>

### 8.4 開発順序と設計へ進む条件

参照元：[文書の順序](../../README.md#documentation)、[最初の受入範囲](#req-initial-acceptance)。対応する設計：[初期版の具体化](../02-external-design/external-design.ja.md#design-next)、[入力設計の位置づけ](../03-internal-design/model-input.ja.md#detail-scope)。

ヒアリングから、現在の作業、主な負担、期待する成果、失敗時の情報、研究者の役割、対象候補、数式による入力を整理した。初期版の範囲を提案するための聞き取りはここで区切る。以下の順序は開発担当の提案であり、要求内容・成果の判定条件に影響する変更は理由とともにレビュー対象にする。

| 段階 | 到達点 | 完了を確認する内容 |
| --- | --- | --- |
| <a name="stage-first-agent"></a>[最初の動作](#stage-first-agent) | PCMの候補提案・計算・検証・再試行を付属エージェントから実行し、PythonとMCPからも計算を利用する | [最初の受入範囲](#req-initial-acceptance)。検証済みとする3検査の基準を維持する |
| <a name="stage-research-models"></a>[研究対象への拡大](#stage-research-models) | T¹,¹・ABLの具体的な作用、PCMからの変形提案へ対応を広げる | 対応する作用・条件と既知結果を明記し、[F-12](#req-f-12)・[F-16](#req-f-16)と3検査を確認する。構成方法は対応対象ごとに決める |
| <a name="stage-research-result"></a>[研究成果と公開](#stage-research-result) | 機械学習探索を追加し、比較評価、模型族の物理解析、配布を完成させる | [開発全体の受入れ](#req-full-acceptance)と[研究成果の確認](#req-research)。最初の動作確認は論文としての完成を意味しない |

| 移行 | 対象範囲について確認する内容 |
| --- | --- |
| <a name="gate-requirements"></a>[要件定義から外部設計](#gate-requirements) | 利用者・目的・現状と目標・優先範囲・制約・受入条件を示し、重大な矛盾と未決事項の扱いをレビューする。初期版のレビュー材料は本書にそろえる |
| <a name="gate-external"></a>[外部設計から内部設計](#gate-external) | 初期版の一連の利用場面について、数式の受け渡し、結果・失敗の表示、方向変更、実行上限と停止、要件との対応を具体例で確認する |
| <a name="gate-internal"></a>[内部設計から実装](#gate-internal) | 対応する処理の責務、データ構造、計算手順、判定の根拠、失敗時の処理と確認例を定め、受入条件に対応付ける |

移行条件は、その時点で開発する範囲に適用する。全模型、全変形方法、一般的な非可積分性の自動証明を解決するまで初期版の実装を待つことはしない。スペクトルパラメータ依存の非自明性は既知PCMの検証方法から具体化し、根拠が未完成の候補は未判定として扱い、受入完了とはしない。数式の取り込みと計算用の表現、接続、停止処理は開発担当が具体案を作る。[第9章](#req-handoff)の設計事項は、対応する実装を進める段階で解決する。

<a name="req-handoff"></a>

## 9. 外部設計への伝達事項

対応する設計：[7. 次に具体化する設計](../02-external-design/external-design.ja.md#design-next)。

上記の機能要件を開発全体の要求とし、優先順は[開発順序](#req-development)に従う。以下は、その要件を具体化するために外部設計へ引き継ぐ事項である。外部設計では、対応する要件番号と確認例を示す。

| 項目 | 確定した要求 | 外部設計で具体化する内容 | 対応要件 | 対応する設計 |
| --- | --- | --- | --- | --- |
| <a name="handoff-models"></a>[対応模型の拡大](#handoff-models) | PCMで最初のエージェント動作を確認し、研究対象候補をT¹,¹・ABL・PCMからの変形とする | 数式から作用・EOMを受け渡す方法、具体的な作用・領域・拘束条件、研究対象への拡大順。入力用の独自様式を利用目的として固定しない | [F-01](#req-f-01)、[F-12](#req-f-12)、[R-01](#req-r-01)、[要件定義書第8.1節](#req-initial-acceptance) | [模型](../02-external-design/external-design.ja.md#input-model)、[入力詳細からの引継ぎ](../03-internal-design/model-input.ja.md#detail-handoff) |
| <a name="handoff-couplings"></a>[Lax接続の存在条件の探索](#handoff-couplings) | 結合定数について、候補が3検査を満たす条件を求め、候補・条件・未解決範囲を返す | 結合定数と探索範囲の指定方法、一般の場合と特殊な値での条件の表示、候補や除外した領域との対応 | [F-12](#req-f-12)、[N-01](#req-n-01) | [Lax接続の存在条件を結合定数について求める](../02-external-design/external-design.ja.md#operation-couplings) |
| <a name="handoff-tools"></a>[計算ツールの追加](#handoff-tools) | ツールの実装・入出力の定義・登録を追加すれば、各利用経路から呼び出せる | ツールが宣言する入出力・適用条件・必要ソフトウェア、登録・選択・単独実行の方法、追加例、候補を共通の検証へ渡す方法 | [N-05](#req-n-05)、[I-01](#req-i-01)、[I-02](#req-i-02)、[I-03](#req-i-03) | [6. 計算ツールを追加する方法](../02-external-design/external-design.ja.md#design-extensions) |
| <a name="handoff-intervention"></a>[実行中の人の介入](#handoff-intervention) | 進捗確認・停止・条件変更・再開と、その履歴を提供する | 各操作の入出力、変更を反映する時点、変更前後の結果の表示と対応付け | [F-10](#req-f-10)、[F-13](#req-f-13)、[R-03](#req-r-03) | [停止・条件変更・再開を行う](../02-external-design/external-design.ja.md#operation-control) |
| <a name="handoff-distribution"></a>[動作環境と配布](#handoff-distribution) | Linux・WSL2、CPUでの標準計算、Pythonパッケージ・ライセンス・利用例の公開を必須とする | 対応する環境とPythonの版、必要資源、追加機能の依存条件、配布先・版の指定方法、ライセンスの選定、導入・MCP接続の手順 | [N-04](#req-n-04)、[N-06](#req-n-06)、[C-01](#req-c-01)、[C-02](#req-c-02) | [具体化予定](../02-external-design/external-design.ja.md#design-next) |
| <a name="handoff-budgets"></a>[実行上限の測定](#handoff-budgets) | 本システムが管理する分岐・再試行・再開を含む全実行に上限を適用し、使用資源と費用を残す | 時間・メモリ・言語モデル利用量・費用の指定単位と計測範囲、並行する計算の集計、停止までの許容時間、取得できない値の表示 | [N-03](#req-n-03)、[C-01](#req-c-01)、[要件定義書第5章](#req-data) | [実行条件](../02-external-design/external-design.ja.md#input-execution) |
| <a name="handoff-essential"></a>[非自明性の検証条件](#handoff-essential) | [F-11](#req-f-11)を最初の受入れから必須とし、未判定の候補を検証済みとして採用しない | 模型ごとの補助線形問題のゲージ群、領域・境界条件、許容する局所ゲージ変換、非自明性の根拠の提示・確認方法 | [F-03](#req-f-03)、[F-04](#req-f-04)、[F-11](#req-f-11)、[N-01](#req-n-01) | [スペクトルパラメータ依存の非自明性](../02-external-design/external-design.ja.md#check-essential)、[局所ゲージ変換の規約](../03-internal-design/model-input.ja.md#conventions-gauge)、[入力詳細からの引継ぎ](../03-internal-design/model-input.ja.md#detail-handoff) |
| <a name="handoff-evaluation"></a>[研究評価](#handoff-evaluation) | 模型族の解析、独立した検算、共通条件での比較、未使用課題での反復評価、資料公開を行う | 課題と比較条件の選定方針、予算・指標・記録・出力の仕様、必要な試行数の決め方。具体的な課題一覧・試行数・集計方法は評価計画に記載する | [R-01](#req-r-01)、[R-02](#req-r-02)、[R-03](#req-r-03)、[N-06](#req-n-06) | [具体化予定](../02-external-design/external-design.ja.md#design-next) |

設計案の作成は開発担当、研究上の条件と受入条件の確認は研究責任者が行う。外部設計の各項目は、対応する外部設計を確定するまでに決める。研究評価に必要な記録・集計の仕様は、評価用機能の設計を確定するまでに定める。具体的な課題一覧・試行数・予算・集計方法は、最終評価を始める前に評価計画で固定する。対応する設計へのリンクは、現在記載されている概要または具体化の予定を指す。設計の完了と実装の受入れは、各項目の確認結果に基づいて判断する。

新たな要求上の未決事項が生じた場合は、内容・担当・決定期限・影響する要件番号を本書に記録する。設計・試験で要件を変更する場合は、本書も更新し、変更理由と影響する要件番号をPRに記録する。

<a name="req-references"></a>

## 10. 参考資料

要求の分類と確認・管理の考え方は、IPAの[ユーザのための要件定義ガイド 第2版](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/youkenteigi20190912.html)と[要件定義の成果物事例](https://www.ipa.go.jp/archive/digital/tools/ep/ep2.html)を参考にした。本書の章立てと受入条件は、この研究用ソフトウェアに合わせて定めている。

構成や計算方法の検討履歴は、[以前の設計案と文献調査](../archive/README.md)に保存している。
