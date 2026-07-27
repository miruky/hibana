# FPS-reFlesh — Claude Code 運用ルール

## モデル・ルーティング方針（トークンマネジメント／必ず適用）

各作業フェーズを以下のモデル×推論努力へ**自動的に**振り分けること。ユーザーが都度指示しなくても、このプロジェクトでの依頼はすべてこの方針で実行する。
（この表は2026-07-04の実証調査で最適化済み: Anthropic公式のorchestrator-worker実証(+90.2%)に骨格が一致。effortは公式ガイダンス「maxは小さな向上に大コスト/コーディング推奨はxhigh」「サブエージェントの機械作業はlow」に従い段階化。）

| フェーズ | モデル | effort | 実行形態 |
|---|---|---|---|
| 司令塔（オーケストレーション・統合・最終判断） | **Fable 5** | **xhigh** | メインループ（このセッション自身。`.claude/settings.json`で既定化済み） |
| 要件定義・設計・計画の統合/判定 | **Fable 5** | **xhigh** | メインループ、または Workflow の judge/synthesize ステージ（`model`省略=継承、`effort:'xhigh'`） |
| ネット検索を伴う調査・リサーチ・大量読み | **Sonnet** | **high** | `subagent_type:'deep-research'`／Workflow `{model:'sonnet', effort:'high'}` |
| 実装・テスト | **Sonnet** | **xhigh** | `subagent_type:'builder'`／Workflow `{model:'sonnet', effort:'xhigh'}` |
| デプロイ・CI操作・定型作業 | **Sonnet** | **high** | `subagent_type:'builder'` か メインのBash直実行 |
| 完全に機械的な一括作業（走査/変換/収集） | **Haiku** | **low** | Workflow `{model:'haiku', effort:'low'}`（そもそもスクリプト化できるならBashで） |
| 敵対的レビューの発見(find)ステージ | **Sonnet** | **xhigh** | Workflow `{model:'sonnet', effort:'xhigh'}` |
| 敵対的レビューの検証(verify)・難所の相談 | **Opus** | **xhigh** | Workflow `{model:'opus', effort:'xhigh'}`（fresh contextでdiffと基準だけ渡す） |

具体的な書き方:
- **Agentツール**: 調査は `subagent_type: 'deep-research'`、実装/テストは `subagent_type: 'builder'`（`.claude/agents/` で model/effort 固定済み）。設計系フォークは `subagent_type: 'fork'`（Fable継承）。
- **Workflowスクリプト**: 上表の model/effort を `agent()` の opts で明示する（**既定は親=Fable 5継承なので、ワーカーには必ず model を明示**しないと最上位モデルで動いてしまう）。
- **難所実装のAdvisorパターン**: 最難関の実装（大規模リファクタ/深いアーキテクチャ判断）は Sonnet に丸投げせず、判断ポイントを Fable 5（私）が設計・指示してから委譲する（公式実測: 品質+2.7pp・コスト−11.9%）。
- 迷ったら「考える仕事・見抜く仕事＝Fable/Opus xhigh、手数の仕事＝Sonnet、機械作業＝Haiku low」。maxは本当に必要な希少ケースのみ。

狙い: 圧倒的パフォーマンス（設計・判断・検証は上位モデルの深い思考）とトークン効率（手数はSonnet/Haikuの適正effort）の両立。

## ラウンド運用（従来どおり）

「最強のFPSにする」系の依頼は R ラウンド方式: 設計ワークフロー（大規模ファンアウト）→ 契約凍結 → 並列実装（非競合ファイル分割）→ 統合 → 敵対的レビュー → 確証findings修正 → ゲート（`npx tsc --noEmit` / `npx eslint src --max-warnings=0` / `npx vitest run` / `npx vite build` 全緑）→ main へ commit+push（自動デプロイ）→ CI+Deploy 確認（Pages一時障害は空コミットで再実行）→ メモリ更新。

## プロジェクト鉄則

- **アセットレスは2026-07-19に完全撤回（ユーザー明示）**。環境・敵兵の見た目は Blender 5.2 LTS で制作し glTF 2.0 (`public/assets/aaa/`) で配信する。正典は `docs/REQUIREMENTS.md`「Blender 配信アセットの実装境界」と `AGENTS.md`。
  - ただし**フェイルオープンは維持**: GLB 欠損/不正 manifest/読込・コンパイル失敗/low画質では決定論的な TypeScript 外装へ必ず戻る。音は引き続き WebAudio 全面合成、UI は DOM+CSS+inline-SVG。
  - **衝突・スポーン・経路・破壊物・物理は TypeScript / Rapier 側が正典**（`src/game/stage.ts` / `stages.ts`）。Blender 資産は表示のみで、当たり判定や動線を宣言で作らない。
  - 配信予算・検証ゲートは `docs/STAGE_WORLD_CATALOG.md` と `npm run blender:validate` に従う。技術PASSは視覚PASSではない（ImageGen参照スコアカードが別ゲート）。
- 固定60Hzロジック＋可変レンダ、snapshot()→DOM一方向、試合ごとdispose、コライダー不変。
- canvas上のパネルに filter/backdrop-filter を載せない。bloom閾値0.9を超える発光を足さない（白飛び再発禁止）。
- 空の明暗調整は match.ts `applySky` の可視空 scale/clamp のみ（envSky=IBLは触らない＝ステージの明るさ維持）。
