# Orion Pipeline 引き継ぎノート

最終更新: 2026-01-23

## 🎉 EP16-30 全エピソード完了！

### ✅ 完了済み作業（2026-01-19〜23）

1. **EP18 拡張版**
   - YAML: 45→53セグメント（+8）
   - 総尺: 7分4秒

2. **EP27 拡張版**
   - YAML: 44→48セグメント（+4）
   - 総尺: 7分5秒

3. **EP28 拡張版（第2回）**
   - YAML: 43→46セグメント（+3）
   - ワツラウィック研究背景、実践アクション追加
   - 総尺: 6分55秒

4. **EP30 拡張版**
   - YAML: 43→50セグメント（+7）
   - 野中郁次郎の時代背景、拈華微笑の詳細、ミラーニューロン発見のドラマ追加
   - 総尺: 7分8秒

5. **EP27-30 TTS完了**
   - 全エピソード音声生成完了
   - Dropbox配置完了

## 次回やること

特になし - EP16-30すべて完了！

---

## 完了済みエピソード

| EP | TTS | XML | SRT | Dropbox | 備考 |
|----|-----|-----|-----|---------|------|
| 16 | ✅ 44/44 | ✅ | ✅ | ✅ | 完了 |
| 17 | ✅ 52/52 | ✅ | ✅ | ✅ | 完了 |
| 18 | ✅ 53/53 | ✅ | ✅ | ✅ | 拡張版(+8seg, 7分) |
| 19 | ✅ 45/45 | ✅ | ✅ | ✅ | 完了 |
| 20 | ✅ 49/49 | ✅ | ✅ | ✅ | 完了 |
| 21 | ✅ 46/46 | ✅ | ✅ | ✅ | 完了 |
| 22 | ✅ 47/47 | ✅ | ✅ | ✅ | 完了 |
| 23 | ✅ 46/46 | ✅ | ✅ | ✅ | 完了 |
| 24 | ✅ 48/48 | ✅ | ✅ | ✅ | 完了 |
| 25 | ✅ 44/44 | ✅ | ✅ | ✅ | 字幕埋込なし(15秒超) |
| 26 | ✅ 46/46 | ✅ | ✅ | ✅ | 完了 |
| 27 | ✅ 48/48 | ✅ | ✅ | ✅ | 拡張版(+4seg, 7分) |
| 28 | ✅ 46/46 | ✅ | ✅ | ✅ | 拡張版x2(+5seg, 7分) |
| 29 | ✅ 42/42 | ✅ | ✅ | ✅ | 完了 (6.9分) |
| 30 | ✅ 50/50 | ✅ | ✅ | ✅ | 拡張版(+7seg, 7.1分) |

---

## 最近の改善 (2026-01-19)

1. **10フレームギャップ追加** - 音声クリップ間に自然な隙間
2. **XML字幕埋込** - FCP7 XMLに字幕トラックを含める
3. **タイムコード修正** - NTSC 29.97fps → 30fpsカウント修正
4. **テキストマッチ優先** - SRT生成で音声内容と字幕を正確にマッチング
5. **Dropboxパス統一** - XMLの音声パスをDropbox内に変更

---

## パイプラインコマンド

```bash
# 単一エピソード実行
cd /Users/delaxstudio/src/delax-ops/ops/media/orion
python3 pipeline/core.py --project OrionEp27

# Dropboxにコピー（XML, SRT, 音声）
DROPBOX_BASE="/Users/delaxstudio/Dropbox/OrionRoom/EP16-30"
cp projects/OrionEp27/output/*.xml "$DROPBOX_BASE/EP27/"
cp projects/OrionEp27/output/*.srt "$DROPBOX_BASE/EP27/"
cp projects/OrionEp27/output/audio/*.mp3 "$DROPBOX_BASE/EP27/"

# XMLパス更新（ソース→Dropbox）
sed -i '' "s|file:///Users/delaxstudio/src/delax-ops/ops/media/orion/projects/OrionEp27/output/audio|file:///Users/delaxstudio/Dropbox/OrionRoom/EP16-30/EP27|g" "$DROPBOX_BASE/EP27/OrionEp27_timeline.xml"
```

---

## ファイル構成

```
projects/OrionEpXX/
├── inputs/
│   ├── epXX.srt          # 元字幕（Single Source of Truth）
│   └── epXXnare.yaml     # ナレーション定義
├── output/
│   ├── audio/            # 生成音声 (mp3)
│   ├── OrionEpXX_timeline.xml
│   ├── OrionEpXX_timeline.csv
│   └── OrionEpXX_timecode.srt
└── exports/
    └── orionepXX_merged.srt
```
