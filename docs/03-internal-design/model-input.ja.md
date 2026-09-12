# 内部設計書：模型とLax候補の入力

対象：nlsm-lax-agent。更新日：2026年9月12日。状態：確認用の草案。以下の型と関数は実装予定の仕様であり、本体は未実装。

本書では、最初の受入対象であるSU(2)主カイラル模型について、入力データ、数式の規約、入力検査と正規化を定める。[外部設計書](../02-external-design/external-design.ja.md)を具体化する内部設計の一部である。

<a name="detail-scope"></a>

## 1. 対象と処理の境界

対応する上位項目：[最初の受入範囲](../01-requirements/requirements.ja.md#req-initial-acceptance)、[後続設計](../02-external-design/external-design.ja.md#design-next)、[文書の順序](../../README.md#documentation)。

本書で実装可能な粒度まで定めるのは、[模型の入力](#detail-model)、[候補の入力](#detail-candidate)、[数式の読み取り](#detail-expressions)、[入力検査](#detail-validation)である。[数学的規約](#detail-conventions)を両入力で共有し、[確認例](#detail-cases)を実装時の試験に用いる。後続項目は[第8章](#detail-handoff)に記す。

Python、MCP、付属エージェントは同じJSON互換データを計算ライブラリへ渡す。入力処理は次の2関数に集約し、ネットワーク、言語モデル、データベースへのアクセスを行わない。登録と記録の保存は呼び出し側が担当する。

| 内部関数 | 引数 | 戻り値・責務 |
| --- | --- | --- |
| <a name="function-model"></a>[`normalize_model(data)`](#function-model) | [模型入力](#detail-model)を表す辞書 | [入力検査結果](#validation-result)。受理時の `value` は、数式を正規化した同じ構造の模型入力 |
| <a name="function-candidate"></a>[`normalize_candidate(data, registered_model)`](#function-candidate) | [候補入力](#detail-candidate)と、呼び出し側が記録から取得した模型 | [入力検査結果](#validation-result)。受理時の `value` は、数式を正規化した同じ構造の候補入力 |

`data` は文字列をキーとする辞書とし、値には辞書、配列、文字列、整数だけを使う。`registered_model` は `run_id`、`model_revision`、受理済みの模型入力 `definition` を持つ内部の記録とする。記録が存在しない場合は `None` を渡す。候補に指定された番号と照合し、別の模型や版への付け替えを防ぐ。入力の受理後に、外部設計の運動方程式の導出や候補検証へ進む。

<a name="detail-conventions"></a>

## 2. 数学的規約

対応する上位項目：[模型](../02-external-design/external-design.ja.md#input-model)、[候補の接続](../02-external-design/external-design.ja.md#input-candidate)。入力で指定する規約名 `su2_left_current_v1` は、この章全体を指す。使用箇所：[模型入力](#detail-model)、[候補入力](#detail-candidate)。

<a name="conventions-model"></a>

### 2.1 場・作用・方程式

参照元：[数学的規約](#detail-conventions)、[模型入力](#detail-model)、[既知模型の確認](#case-known)。

時空は、固定したLorentz計量を持つ可縮な開領域とする。座標を $`x^\pm=t\pm x`$、微分を $`\partial_\pm=\partial/\partial x^\pm=(\partial_t\pm\partial_x)/2`$ と定義する。変分する場は滑らかな群値場 $`g(x^+,x^-)\in SU(2)`$ のみであり、変分はコンパクトな台を持つ。境界条件と時空計量の変分による拘束条件は課さない。

Lie代数の基底は $`T_a=-i\sigma_a/2`$ とする。ここで $`i^2=-1`$、 $`\sigma_a`$ はPauli行列、 $`a=1,2,3`$ である。規格化は $`[T_a,T_b]=\epsilon_{ab}{}^cT_c`$、 $`\epsilon_{12}{}^3=1`$、 $`\mathrm{tr}(T_aT_b)=-\delta_{ab}/2`$ とする。`trace_fundamental` はこの2次元表現の通常の行列トレースを表す。

左不変カレントと作用を次のように定める。結合定数 $`\kappa`$ は正の実定数とし、時空座標に依存しない。

$$
j_\pm=g^{-1}\partial_\pm g=j_\pm^aT_a,
\qquad
S[g]=-\frac{1}{2\kappa^2}\int dx^+dx^-\,\mathrm{tr}(j_+j_-).
$$

作用から方程式を導く際は、 $`\delta g=g\varepsilon`$ と置き、 $`\delta j_\pm=\partial_\pm\varepsilon+[j_\pm,\varepsilon]`$ を代入する。トレースの巡回性と部分積分により、 $`\delta S=(2\kappa^2)^{-1}\int dx^+dx^-\mathrm{tr}(\varepsilon\mathcal E)`$ を得る。運動方程式とMaurer–Cartan恒等式を、それぞれ次の左辺で記録する。

$$
\mathcal E=\partial_+j_-+\partial_-j_+=0,
\qquad
\mathcal M=\partial_+j_- -\partial_-j_+ +[j_+,j_-]=0.
$$

運動方程式は $`\mathcal E^a=0`$ の3成分全部である。恒等式はカレントの定義から導き、運動方程式とは別に記録する。導出では入力された作用の係数と $`\kappa>0`$ を保持し、零でない係数を除いた過程を残す。カレントだけを独立な無拘束の場として変分することや、候補から運動方程式を選ぶことはしない。この表現はDriezenの講義録の[第4.2節・式(4.19)–(4.22)](https://arxiv.org/pdf/2112.14628)に対応し、作用の係数と基底の規格化は本書で固定している。

<a name="conventions-gauge"></a>

### 2.2 接続・スペクトルパラメータ・ゲージ変換

対応する上位項目：[非自明性の検証条件](../01-requirements/requirements.ja.md#handoff-essential)、[F-11](../01-requirements/requirements.ja.md#req-f-11)。参照元：[数学的規約](#detail-conventions)、[候補のゲージ条件](#candidate-gauge)。

スペクトルパラメータ $`z`$ は複素数で、時空座標、場、結合定数から独立とする。許容領域 $`Z`$ は[候補入力の多項式](#candidate-spectrum)で指定する。接続 $`\mathcal L_\pm(z)`$ は $`\mathfrak{sl}_2(\mathbb C)`$ に値を取り、補助線形問題と曲率の符号を次のように固定する。

$$
(\partial_\pm+\mathcal L_\pm)\psi=0,
\qquad
F=\partial_+\mathcal L_- -\partial_-\mathcal L_+ +[\mathcal L_+,\mathcal L_-].
$$

$`\psi`$ は2成分の補助関数である。ゲージ群を $`SL_2(\mathbb C)`$ とし、 $`\psi'=h\psi`$ に対応する変換を

$$
\mathcal L'_\pm=h\mathcal L_\pm h^{-1}-(\partial_\pm h)h^{-1}
$$

と定める。許容する $`h`$ は、時空座標、 $`g`$ とその有限階の微分、 $`\kappa`$、 $`z`$ の局所関数である。場とその微分について滑らかで、 $`z`$ について正則、かつ可逆であることを要求する。微分の階数にあらかじめ上限を置かない。線積分や補助関数 $`\psi`$ への依存は、この局所関数に含めない。

非自明性は、一般の場の値とその微分の値の開領域、および $`Z`$ 内の一般のスペクトル点の開近傍で検査する。局所的に許容される変換も除去可能性の対象とし、領域全体での単一値性だけを障害として採用しない。変換後の接続に候補入力と同じ式の形を要求しない。運動方程式、恒等式とそれらの微分の下で $`\partial_z\mathcal L'_\pm=0`$ とできるかが判定対象となる。この局所ゲージ同値の考え方は[Marvan, 第1–2節](https://arxiv.org/pdf/0804.2031)を参照する。

<a name="detail-model"></a>

## 3. 模型入力

対応する上位項目：[F-01](../01-requirements/requirements.ja.md#req-f-01)、[模型](../02-external-design/external-design.ja.md#input-model)、[模型と計算条件の登録](../02-external-design/external-design.ja.md#operation-register)。参照元：[対象範囲](#detail-scope)、[模型の入力処理](#function-model)。

全項目を必須とし、省略時の既定値は設けない。この版で受理する模型は[第2.1節](#conventions-model)の作用である。模型名を選ぶ補助機能も、以下の完全なデータへ展開して利用者に返し、保存する。

| 項目 | 型と受理条件 |
| --- | --- |
| <a name="model-version"></a>[`schema_version`](#model-version) | 整数 `1`。入力形式の版。真偽値は整数として受理しない |
| <a name="model-kind"></a>[`model_type`, `conventions`](#model-kind) | 文字列 `su2_pcm`, `su2_left_current_v1`。[第2章](#detail-conventions)の群、基底、微分、符号を固定する |
| <a name="model-field"></a>[`field`](#model-field) | `name: "g"`, `target: "SU2"` を持つオブジェクト |
| <a name="model-coupling"></a>[`coupling`](#model-coupling) | `name: "kappa"`, `domain: "positive_real"` を持つオブジェクト。記号のまま保持し、全ての正の実数を対象とする |
| <a name="model-action"></a>[`action`](#model-action) | `measure` は `['x_plus','x_minus']`、`prefactor` は `kappa` の有理式、`pairing` は `trace_fundamental`、`currents` は `['j_plus','j_minus']`。係数が厳密に `-1/(2*kappa**2)` と等しいことを確認する |
| <a name="model-domain"></a>[`domain`](#model-domain) | 下例の4項目を文字列で指定する。それぞれ時空領域、場の滑らかさ、境界条件、変分の条件を表し、値の意味は[第2.1節](#conventions-model)で定義する |

```json
{
  "schema_version": 1,
  "model_type": "su2_pcm",
  "conventions": "su2_left_current_v1",
  "field": {"name": "g", "target": "SU2"},
  "coupling": {"name": "kappa", "domain": "positive_real"},
  "action": {
    "measure": ["x_plus", "x_minus"],
    "prefactor": "-1/(2*kappa**2)",
    "pairing": "trace_fundamental",
    "currents": ["j_plus", "j_minus"]
  },
  "domain": {
    "spacetime": "contractible_lorentzian_patch",
    "field_regularity": "smooth",
    "boundary_conditions": "none",
    "variation": "compact_support"
  }
}
```

任意の作用、座標表示の計量や反対称テンソル、追加の拘束条件を受理する形式は、[対応模型を拡大する設計](#detail-handoff)で追加する。この版に別の作用を渡した場合は、未対応として理由を返す。

<a name="detail-candidate"></a>

## 4. 候補入力

対応する上位項目：[F-02](../01-requirements/requirements.ja.md#req-f-02)、[保存する入力](../01-requirements/requirements.ja.md#data-input)、[候補の接続](../02-external-design/external-design.ja.md#input-candidate)。参照元：[対象範囲](#detail-scope)、[候補の入力処理](#function-candidate)。

この版で受理する接続は、カレントに線形で、係数が $`z`$ の有理関数であるものとする。各成分を、下式の4個の $`3\times3`$ 行列 $`A_{\mu\nu}(z)`$ で表す。 $`\mu,\nu`$ は時空の `plus`, `minus` に対応する。

$$
\mathcal L_\mu(z)=\sum_{\nu=+,-}\sum_{a,b=1}^3
(A_{\mu\nu}(z))^a{}_b\,j_\nu^bT_a.
$$

| 項目 | 型と受理条件 |
| --- | --- |
| <a name="candidate-version"></a>[`schema_version`](#candidate-version) | 整数 `1` |
| <a name="candidate-model"></a>[`model_ref`](#candidate-model) | 空でない文字列 `run_id` と正の整数 `model_revision`。登録記録の両方の値と一致すること |
| <a name="candidate-representation"></a>[`representation`](#candidate-representation) | 文字列 `su2_current_linear_v1`。この章の行列による表現を指す |
| <a name="candidate-spectrum"></a>[`spectral_parameter`](#candidate-spectrum) | `name: "z"`, `base: "complex_plane"`, `exclude_zeros`。最後の値は `z` の非零多項式を表す文字列の配列。 $`Z=\{z\in\mathbb C\mid p(z)\ne0\text{ for every listed }p\}`$ と定義し、空配列なら複素平面全体とする |
| <a name="candidate-components"></a>[`components`](#candidate-components) | `plus`, `minus` の両方を必須とし、各値は項の配列。各項は `current` と `matrix` を持つ。`current` は `j_plus` または `j_minus`、`matrix` は数式文字列からなる3行3列の配列。行は出力の基底添字、列はカレントの添字。同じ成分内でカレント名を重複させない。省略した項は零行列、空配列は零接続成分を表す |
| <a name="candidate-gauge"></a>[`gauge_equivalence`](#candidate-gauge) | 下例の4項目を必須とし、群、局所性、正則性、検査領域の値を[第2.2節](#conventions-gauge)の意味で固定する |

以下は既知の候補 $`\mathcal L_\pm=j_\pm/(1\mp z)`$ の完全な入力例である（[Driezen, 式(4.61)](https://arxiv.org/pdf/2112.14628)）。模型の登録によって例示した実行番号と版が返ったものとする。実際には登録結果の値を使用する。

```json
{
  "schema_version": 1,
  "model_ref": {"run_id": "example-run-001", "model_revision": 1},
  "representation": "su2_current_linear_v1",
  "spectral_parameter": {
    "name": "z", "base": "complex_plane", "exclude_zeros": ["1-z", "1+z"]
  },
  "components": {
    "plus": [{"current": "j_plus", "matrix": [
      ["1/(1-z)", "0", "0"],
      ["0", "1/(1-z)", "0"],
      ["0", "0", "1/(1-z)"]
    ]}],
    "minus": [{"current": "j_minus", "matrix": [
      ["1/(1+z)", "0", "0"],
      ["0", "1/(1+z)", "0"],
      ["0", "0", "1/(1+z)"]
    ]}]
  },
  "gauge_equivalence": {
    "group": "SL2C", "dependence": "local_finite_jet",
    "regularity": "smooth_fields_holomorphic_z", "scope": "generic_local"
  }
}
```

入力の式の形は候補の受付範囲であり、[ゲージ変換の範囲](#conventions-gauge)を制限しない。カレントの高階微分、場への直接依存、結合定数への依存、一般のスペクトル関数を含む候補は、この版では未対応とする。数値探索からは、有理関数へ厳密に再構成できた候補をこの形式で渡す。近似値を自動で有理数へ丸める処理は入力検査に含めない。

<a name="detail-expressions"></a>

## 5. 数式の読み取りと正規化

対応する上位項目：[保存する入力](../01-requirements/requirements.ja.md#data-input)、[F-09](../01-requirements/requirements.ja.md#req-f-09)。参照元：[対象範囲](#detail-scope)、[入力検査](#detail-validation)。

数式は文字列で受け取り、整数、括弧、単項の `+ -`、二項の `+ - * /`、整数乗 `**` だけを認める。整数リテラルは10進の数字列とし、指数は符号付き整数リテラルに限る。`^`、小数、関数呼出し、属性参照、添字、暗黙の乗算は受理しない。整数以外の厳密な数は `1/2`、`-3/5` のように書く。

| 使用箇所 | 許す記号・係数 | 追加条件 |
| --- | --- | --- |
| <a name="expression-action"></a>[作用の係数](#expression-action) | `kappa` と有理数 | 正の実数全体で定義され、[指定した作用](#model-action)と厳密に一致する |
| <a name="expression-candidate"></a>[接続の係数](#expression-candidate) | `z`, `I` と有理数。`I` は虚数単位 | [スペクトル領域](#candidate-spectrum)で全ての分母が零にならない |
| <a name="expression-domain"></a>[領域の除外多項式](#expression-domain) | `z`, `I` と有理数 | 約分後の分母は定数、分子は零でない |

読み取りでは、前後の空白を除き、Pythonの `tokenize` で数値トークンが10進の数字列であることと、記号名が上表の許可名に一致することを確認する。空白、許可した名前・数値・演算子・括弧以外のトークンは拒否する。続いて [`ast.parse(..., mode="eval")`](https://docs.python.org/3/library/ast.html#ast.parse) を用い、許可した構文木の節点だけを走査してSymPyの整数、有理数、記号と四則演算へ構築する。Pythonの `eval` と、未検査の文字列を直接評価する読み取り関数は使わない。真偽値、未宣言の記号、整数以外の指数は拒否する。

有理式は有理数と虚数単位を係数とする多項式の商として扱い、SymPyの [`cancel`](https://docs.sympy.org/latest/modules/polys/reference.html#sympy.polys.polytools.cancel) によって共通因子を約分する。保存用の式はその結果の `str` とし、入力時と同じ構文で再読できることを確認する。作用の実係数には虚数単位を許さない。数式処理系の版は実行記録に保存する。正規化した文字列の一致を、異なる式・候補全般の同値性の判定には使わない。

各除算の右辺、または負の整数乗の底について、約分した分子が零でないという条件を**元の構文木の走査中に**収集する。零多項式になれば除算不能として拒否する。係数全体の約分後にも、この条件を保持する。例えば `(z-2)/(z-2)` を `1` に約分しても、元の入力の条件 $`z\ne2`$ は残る。

候補では、収集した非零条件の各多項式について、全ての零点が `exclude_zeros` で除外されることを確認する。具体的には、多項式の重複因子を除いて最高次係数を1にそろえ、前者が除外多項式の積の重複因子を除いたものを割り切るかを厳密に調べる。除外が空なら積は `1` とする。余分に指定された除外領域は保持する。作用では、収集した条件が $`\kappa>0`$ の全域で満たされることを有理係数多項式の実根の厳密な分離によって確認し、正の根を持つ分母は拒否する。

除外多項式自身の文字列も同じ走査で読み、除算がある場合はその分母の条件を領域の検査に含める。例えば `(z-2)/(z-2)` という除外指定は、約分後が定数であっても $`z=2`$ で定義されないため、この指定だけでは受理しない。領域の自己参照を避けるため、まず約分後の全除外多項式から領域を定め、その領域で元の全ての式が定義されるかを検査する。

<a name="detail-validation"></a>

## 6. 入力検査の手順と結果

対応する上位項目：[F-01](../01-requirements/requirements.ja.md#req-f-01)、[F-02](../01-requirements/requirements.ja.md#req-f-02)、[N-01](../01-requirements/requirements.ja.md#req-n-01)、[入力と計算の記録](../02-external-design/external-design.ja.md#design-inputs)。参照元：[対象範囲](#detail-scope)、[模型の入力処理](#function-model)、[候補の入力処理](#function-candidate)。

次の順に検査し、最初の失敗で戻る。同じ段階では[模型入力](#detail-model)・[候補入力](#detail-candidate)の表の順に項目を調べ、配列は先頭から、行列は行・列の順に調べる。全オブジェクトで未知のキーを拒否する。JSON文字列の重複キーは辞書へ変換する前に接続層で拒否する。

| 順序 | 処理 | 失敗時のコード |
| --- | --- | --- |
| <a name="validation-shape"></a>[1. 構造](#validation-shape) | 必須項目、型、未知のキー、3行3列、カレント名の重複を確認する | `INVALID_STRUCTURE` |
| <a name="validation-support"></a>[2. 対応範囲](#validation-support) | 入力版、模型・規約・表現、場と結合定数、領域、ゲージ条件の指定を確認する | `UNSUPPORTED_VERSION` または `UNSUPPORTED_SPECIFICATION` |
| <a name="validation-reference"></a>[3. 対象模型](#validation-reference) | 候補では `registered_model` と実行番号・版を照合する。記録が存在しない場合も失敗とする。模型入力ではこの段階を飛ばす | `MODEL_REFERENCE_MISMATCH` |
| <a name="validation-expression"></a>[4. 数式](#validation-expression) | [第5章](#detail-expressions)に従って構文と記号を調べ、有理式と元の分母の条件を得る | `INVALID_EXPRESSION`、`UNSUPPORTED_EXPRESSION`、`UNDECLARED_SYMBOL`、`ZERO_DENOMINATOR` |
| <a name="validation-domain"></a>[5. 数学的な入力条件](#validation-domain) | 作用が指定した式と等しいか、除外指定が非零多項式か、元の全ての分母が適用領域で零にならないかを調べる | `UNSUPPORTED_ACTION`、`INVALID_SPECTRAL_DOMAIN`、`UNDECLARED_SINGULARITY` |
| <a name="validation-normalize"></a>[6. 正規化](#validation-normalize) | 数式を正規化する。候補の項は `j_plus`, `j_minus` の順、除外多項式は重複因子を除き最高次係数を1にした文字列の辞書順とし、同一の除外多項式を重複保存しない | 正規化した入力を返す |

構文として読めない式には `INVALID_EXPRESSION`、関数や非整数乗など対応外の構文には `UNSUPPORTED_EXPRESSION` を返す。対応外の仕様や作用は、物理的に不正であるという判定を意味しない。資源上限による中断や内部の例外は、上表の入力エラーへ変換せず、呼び出し元の計算管理へ伝える。

<a name="validation-result"></a>

### 6.1 戻り値と保存への引渡し

対応する上位項目：[F-08](../01-requirements/requirements.ja.md#req-f-08)、[保存する入力](../01-requirements/requirements.ja.md#data-input)。参照元：[入力検査](#detail-validation)、[模型の入力処理](#function-model)、[候補の入力処理](#function-candidate)。

戻り値は `status`, `value`, `error` の3項目とする。受理時は `status: "accepted"`、`value` に正規化した入力、`error: null` を返す。拒否時は `status: "rejected"`、`value: null` とし、`error` に文字列の `code`, `path`, `message` を返す。`path` はJSONのルートを空文字列、下位項目を `/` 区切り、配列添字を0始まりで示す。キー中の `~`, `/` はそれぞれ `~0`, `~1` と表す。

例えば、候補の `1/(1-z)` に対して `z=1` を除外しなかった場合は次を返す。

```json
{
  "status": "rejected", "value": null,
  "error": {
    "code": "UNDECLARED_SINGULARITY",
    "path": "/components/plus/0/matrix/0/0",
    "message": "分母の非零条件 z - 1 != 0 がスペクトル領域に含まれていません。"
  }
}
```

呼び出し側は元の入力と戻り値を記録し、受理時だけ `value` を後続計算へ渡す。登録記録には規約名とその定義の版を保存し、規約の更新時にも既存の記録を読み替えない。候補は照合した実行番号と模型の版に対応付ける。拒否された入力によって、受理済みの模型や候補を上書きしない。

`accepted` は入力として扱えるという意味である。零接続も受理し、後続の3検査で判定する。この関数群は零曲率、全方程式の回収、非自明性の判定値を生成しない。

<a name="detail-cases"></a>

## 7. 確認例

対応する上位項目：[既知のLax接続](../01-requirements/requirements.ja.md#accept-known-lax)、[運動方程式を表さない候補](../01-requirements/requirements.ja.md#accept-missing-equations)、[除去可能なスペクトル依存](../01-requirements/requirements.ja.md#accept-removable-parameter)、[保存した結果の再検算](../01-requirements/requirements.ja.md#accept-recheck)。参照元：[対象範囲](#detail-scope)。

以下は実装時に確認する期待結果である。本書の入力検査と、後続の物理検証の結果を分けて示す。

| 入力 | 入力検査の期待結果 | 後続計算で確認すること |
| --- | --- | --- |
| <a name="case-known"></a>[第3・4章の完全な入力例](#case-known) | 受理 | [第2.1節](#conventions-model)の運動方程式全体を導出し、下記の曲率恒等式と非自明性を確認する |
| <a name="case-zero"></a>[両成分を空配列にした零接続](#case-zero) | 受理 | 零曲率は成立、運動方程式の回収と非自明性は不成立 |
| <a name="case-current"></a>[両成分を対応するカレント自身にする](#case-current) | 受理。係数は単位行列、除外指定は空配列 | 曲率は恒等式だけで零になる。運動方程式の回収と非自明性は不成立 |
| <a name="case-gauge"></a>[下記のゲージ変換で依存を付けたカレント](#case-gauge) | 受理 | 具体的な逆変換で依存が除去でき、非自明性は不成立 |
| <a name="case-pole"></a>[既知候補で除外指定を空配列にする](#case-pole) | `UNDECLARED_SINGULARITY` | 後続計算へ渡さない |
| <a name="case-cancel"></a>[係数に `(z-2)/(z-2)` を使う](#case-cancel) | `z-2` の零点を除外すれば受理、除外しなければ `UNDECLARED_SINGULARITY` | 正規化後も指定した領域と元の入力を再現する |
| <a name="case-format"></a>[小数 `0.5`、`sin(z)`、未宣言の `w` を係数に使う](#case-format) | 前2者は `UNSUPPORTED_EXPRESSION`、最後は `UNDECLARED_SYMBOL` | 近似や記号の読み替えを行わない |
| <a name="case-reference"></a>[登録記録と異なる模型の版を指定する](#case-reference) | `MODEL_REFERENCE_MISMATCH` | 既存の候補・記録を変更しない |
| <a name="case-recheck"></a>[受理した入力を保存して再読する](#case-recheck) | 同じ数式処理系の版で同じ正規化結果 | 言語モデルの呼出しなしで、模型・候補・領域・規約を復元する |

既知候補の曲率は、本書の符号で次のように分解できる。

$$
F(z)=\frac{\mathcal M-z\mathcal E}{1-z^2}.
$$

$`\mathcal M=0`$ の下で全ての $`z\in Z`$ に対する零曲率から $`\mathcal E=0`$ を回収する。 $`z=0`$ だけでは回収できないことも確認する。この式の確認に加え、非自明性の根拠を検証器で確認することが最初の受入れに必要である。

見かけ上の依存を付ける例には $`h(z)=\mathrm{diag}(z,z^{-1})`$、 $`Z=\mathbb C\setminus\{0\}`$ を使う。両成分で $`\mathcal L_\pm=h j_\pm h^{-1}`$ とし、 $`A_{++}=A_{--}`$ を以下の行列、混合する2行列を零とする。

$$
A_{++}=A_{--}=\begin{pmatrix}
(z^2+z^{-2})/2 & -i(z^2-z^{-2})/2 & 0\\
i(z^2-z^{-2})/2 & (z^2+z^{-2})/2 & 0\\
0&0&1
\end{pmatrix}.
$$

入力には `I`, `**`, `/` で各要素を記述し、`exclude_zeros: ["z"]` とする。逆変換 $`h^{-1}`$ によって $`j_\pm`$ が得られる。これは[第2.2節](#conventions-gauge)の許容する変換の具体例であり、式に $`z`$ が現れることだけでは採用できない候補となる。

<a name="detail-handoff"></a>

## 8. 後続設計への引継ぎ

対応する上位項目：[後続設計](../02-external-design/external-design.ja.md#design-next)、[対応模型の拡大](../01-requirements/requirements.ja.md#handoff-models)、[非自明性の検証条件](../01-requirements/requirements.ja.md#handoff-essential)。参照元：[対象範囲](#detail-scope)、[模型入力](#detail-model)。

次の文書では、この入力から零曲率・運動方程式全体の回収・非自明性を検査する手順、返す根拠と未判定の条件を定める。特に非自明性については、本書の局所ゲージ変換の範囲を覆う証明方法が必要である。有限の形の変換を探索して見つからなかったことを、成立の根拠にはしない。

本書は最初の模型の入力に範囲を限定している。有限個の結合定数を持つ模型族と探索条件、一般の候補表現は、対応する型と入力例を追加する後続設計へ引き継ぐ。既存の入力形式の意味を変える場合は版を上げる。各操作の公開名と通信形式、実行・保存管理、配布、評価計画も外部設計の順序に従って具体化する。
