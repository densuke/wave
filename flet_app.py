import sys
import os
import importlib
import flet as ft
import subprocess
import typing
import shutil
import numpy as np
from lib.utils import set_config_value, load_config_toml

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
config_template_path = os.path.join(WORK_DIR, "config.toml.in")
config_path = os.path.join(WORK_DIR, "config.toml")
if not os.path.exists(config_path):
    shutil.copy2(config_template_path, config_path)

sys.path.insert(0, os.path.join(WORK_DIR, "lib"))
# モジュールのimport
encode = importlib.import_module("encode")
decode_mod = importlib.import_module("decode")
noise_mod = importlib.import_module("noise")

# config.toml自動生成
config_template_path = os.path.join(WORK_DIR, "config.toml.in")
config_path = os.path.join(WORK_DIR, "config.toml")
if not os.path.exists(config_path):
    shutil.copy2(config_template_path, config_path)

# UIコールバック

def main(page: ft.Page) -> None:
    page.title = "FSKエンコード/デコードUI"

    # 入力欄（ファイル名入力のみ、初期値はsample.txt）
    file_name_input = ft.TextField(label="変換元ファイル名（パス）", value="sample.txt", width=400)
    file_name_label = ft.Text(value="", size=12)

    # ノイズレベル
    noise_slider = ft.Slider(min=0, max=8, divisions=8, label="ノイズレベル: {value}", value=0)

    # config.tomlから初期値取得
    config = load_config_toml(config_path)
    bitrate_init = config.get("BITRATE", 1200)

    # サンプリングレート選択肢（FSKビットレートに応じて推奨値を用意）
    sample_rate_options = [8000, 9600, 16000, 22050, 44100, 48000]
    sample_rate_dropdown = ft.Dropdown(
        label="サンプリングレート",
        options=[ft.dropdown.Option(str(sr)) for sr in sample_rate_options],
        value="9600",
        width=180
    )

    # ビットレート選択肢（9600Hzサンプリングで4800までOK）
    bitrate_options = [300, 600, 1200, 2400, 4800]
    bitrate_dropdown = ft.Dropdown(
        label="ビットレート",
        options=[ft.dropdown.Option(str(b)) for b in bitrate_options],
        value=str(bitrate_init) if bitrate_init in bitrate_options else "1200",
        width=180
    )

    def on_sample_rate_dropdown_change(e: ft.ControlEvent) -> None:
        if sample_rate_dropdown.value is not None:
            set_config_value("SAMPLE_RATE", sample_rate_dropdown.value, config_path)
        page.update()
    sample_rate_dropdown.on_change = on_sample_rate_dropdown_change

    def on_bitrate_dropdown_change(e: ft.ControlEvent) -> None:
        if bitrate_dropdown.value is not None:
            v = int(bitrate_dropdown.value)
            set_config_value("BITRATE", v, config_path)
        page.update()
    bitrate_dropdown.on_change = on_bitrate_dropdown_change

    def set_noise_level_config(level: int) -> None:
        set_config_value("NOISE_LEVEL", level, config_path)
    def set_bitrate_config(bitrate: int) -> None:
        set_config_value("BITRATE", bitrate, config_path)

    # 実行ボタン
    run_btn = ft.ElevatedButton("変換開始", disabled=False)

    # 結果表示
    result_text = ft.Text(value="", size=14)
    md5_text = ft.Text(value="", size=14)
    # スピナー
    progress_ring = ft.ProgressRing(visible=False)

    # 音声再生ボタン
    play_encode_btn = ft.ElevatedButton("エンコードWAV再生", disabled=True)
    play_noise_btn = ft.ElevatedButton("ノイズ付加WAV再生", disabled=True)
    # Windows外部再生案内フラグ
    wav_play_notice_shown = {"encode": False, "noise": False}

    # MD5表示用テキスト（各WAVファイルごと）
    encode_wav_md5_text = ft.Text(value="", size=12, color="blue")
    noise_wav_md5_text = ft.Text(value="", size=12, color="blue")

    # ファイルパス保持
    encode_wav_path = os.path.join(WORK_DIR, "static", "output_orig.wav")  # エンコードWAVはstatic/output_orig.wav
    noise_wav_path = os.path.join(WORK_DIR, "static", "output.wav")        # ノイズ付加WAVはstatic/output.wav
    orig_file_path = ""

    # Audioコントロール削除（外部アプリ再生に戻す）

    def on_run(e: ft.ControlEvent) -> None:
        # スピナー表示
        progress_ring.visible = True
        page.update()
        # ファイル名取得
        nonlocal orig_file_path
        file_path_from_input = file_name_input.value.strip() if file_name_input.value else ""
        if file_path_from_input:
            orig_file_path = file_path_from_input
        if not orig_file_path:
            result_text.value = "ファイル名を入力または選択してください"
            page.update()
            return
        noise_level = int(noise_slider.value)
        bitrate = int(bitrate_dropdown.value) if bitrate_dropdown.value is not None else 1200
        sample_rate = int(sample_rate_dropdown.value) if sample_rate_dropdown.value is not None else 9600
        set_noise_level_config(noise_level)
        set_bitrate_config(bitrate)
        set_config_value("SAMPLE_RATE", sample_rate)
        # staticディレクトリ作成（なければ）
        static_dir = os.path.join(WORK_DIR, "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
        # ファイルエンコード
        bit_string = encode.file_to_bitstring(orig_file_path)
        encode.validate_bit_string(bit_string)
        encode.generate_tone(bit_string, duration=1.0/bitrate, sample_rate=sample_rate, noise_level=noise_level, output_path=encode_wav_path)
        # ノイズ付加
        import shutil
        shutil.copy2(encode_wav_path, noise_wav_path)
        with open(noise_wav_path, "rb") as wf:
            import wave
            with wave.open(wf, 'rb') as wavf:
                params = wavf.getparams()
                frames = wavf.readframes(wavf.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16)
        noisy_samples = noise_mod.add_noise(samples, sample_rate, noise_level)
        with wave.open(noise_wav_path, 'wb') as wf:
            wf.setparams(params)
            wf.writeframes(noisy_samples.tobytes())
        # デコード
        with open(orig_file_path, 'rb') as f:
            orig_bytes = f.read()
        correct_bit_string = ''.join(f'{b:08b}' for b in orig_bytes)
        bit_string_decoded = decode_mod.decode_tone(noise_wav_path, correct_bit_string, duration=1.0/bitrate, sample_rate=sample_rate)
        restored_bytes = decode_mod.bitstring_to_bytes(bit_string_decoded)
        # エンコードWAVのMD5
        import hashlib
        with open(encode_wav_path, 'rb') as f:
            encode_wav_md5 = hashlib.md5(f.read()).hexdigest()
        encode_wav_md5_text.value = f"MD5: {encode_wav_md5}"
        # ノイズ付加WAVのMD5
        with open(noise_wav_path, 'rb') as f:
            noise_wav_md5 = hashlib.md5(f.read()).hexdigest()
        noise_wav_md5_text.value = f"MD5: {noise_wav_md5}"
        # 全体比較用MD5
        md5_text.value = ""
        orig_md5 = hashlib.md5(orig_bytes).hexdigest()
        restored_md5 = hashlib.md5(restored_bytes).hexdigest()
        compare_result = f"[MD5] 元データ: {orig_md5}\n[MD5] 復元データ: {restored_md5}"
        if orig_md5 == restored_md5:
            compare_result += "\n[OK] MD5一致: 完全復元"
        else:
            compare_result += "\n[NG] MD5不一致: データ化けあり"
        md5_text.value = compare_result
        result_text.value = "デコード結果を表示しました（内容は非表示）"
        # ボタン有効化
        play_encode_btn.disabled = False
        play_noise_btn.disabled = False
        stop_encode_btn.disabled = False
        stop_noise_btn.disabled = False
        # スピナー非表示
        progress_ring.visible = False
        page.update()

    run_btn.on_click = on_run

    # 再生停止用
    play_process: dict[str, typing.Any] = {"encode": None, "noise": None}
    # 再生インジケーター
    play_indicator = ft.Text(value="", size=12)
    play_indicator_stop_flag: dict[str, bool] = {"encode": False, "noise": False}

    import time
    import threading
    import wave as pywave

    def format_time(sec: float) -> str:
        m = int(sec) // 60
        s = int(sec) % 60
        return f"{m}:{s:02d}"

    def start_play_indicator(path: str, kind: str) -> None:
        try:
            with pywave.open(path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                total_sec = frames / rate
        except Exception:
            play_indicator.value = ""
            page.update()
            return
        start_time = time.time()
        play_indicator_stop_flag[kind] = False
        def update():
            while not play_indicator_stop_flag[kind]:
                elapsed = time.time() - start_time
                if elapsed > total_sec:
                    elapsed = total_sec
                play_indicator.value = f"再生中: {format_time(elapsed)} / {format_time(total_sec)}"
                page.update()
                if elapsed >= total_sec:
                    break
                time.sleep(0.5)
            play_indicator.value = ""
            page.update()
        t = threading.Thread(target=update, daemon=True)
        t.start()

    def stop_play_indicator(kind: str) -> None:
        play_indicator_stop_flag[kind] = True

    def stop_wav(kind: str) -> None:
        proc = play_process.get(kind)
        if proc is not None and hasattr(proc, 'poll') and proc.poll() is None:
            proc.terminate()
        play_process[kind] = None
        stop_play_indicator(kind)

    def play_wav(path: str, kind: str) -> None:
        print(f"[再生] {kind}: {path}")
        stop_wav(kind)
        start_play_indicator(path, kind)
        # 外部アプリでwav再生
        if os.name == "posix":
            proc = subprocess.Popen(["afplay", path])
        else:
            proc = subprocess.Popen(["start", path], shell=True)
        play_process[kind] = proc

    def play_encode_btn_click(e):
        if os.name == "nt" and not wav_play_notice_shown["encode"]:
            page.snack_bar = ft.SnackBar(ft.Text("外部プレイヤーで流しているので、停止は外部プレイヤーの終了をしてから押してください"), open=True)
            page.update()
            wav_play_notice_shown["encode"] = True
        play_wav(encode_wav_path, "encode")

    def play_noise_btn_click(e):
        if os.name == "nt" and not wav_play_notice_shown["noise"]:
            page.snack_bar = ft.SnackBar(ft.Text("外部プレイヤーで流しているので、停止は外部プレイヤーの終了をしてから押してください"), open=True)
            page.update()
            wav_play_notice_shown["noise"] = True
        play_wav(noise_wav_path, "noise")

    play_encode_btn.on_click = play_encode_btn_click
    play_noise_btn.on_click = play_noise_btn_click
    stop_encode_btn = ft.ElevatedButton("エンコード再生停止", on_click=lambda e: stop_wav("encode"), disabled=True)
    stop_noise_btn = ft.ElevatedButton("ノイズ再生停止", on_click=lambda e: stop_wav("noise"), disabled=True)

    # 再生ボタン有効化時に停止ボタンも有効化
    def enable_play_buttons() -> None:
        play_encode_btn.disabled = False
        play_noise_btn.disabled = False
        stop_encode_btn.disabled = False
        stop_noise_btn.disabled = False

    # レイアウト
    # audioタグ埋め込み削除

    # WindowsではNoneを除外したリストを構築
    def filter_none(lst):
        return [x for x in lst if x is not None]

    page.add(
        ft.Row([
            ft.Column([
                ft.Text("ノイズレベル", size=14, weight=ft.FontWeight.BOLD),
                noise_slider,
                ft.Text("サンプリングレート", size=14, weight=ft.FontWeight.BOLD),
                sample_rate_dropdown,
                ft.Text("ビットレート", size=14, weight=ft.FontWeight.BOLD),
                bitrate_dropdown,
            ], alignment=ft.MainAxisAlignment.START, width=220),
            ft.VerticalDivider(width=1),
            ft.Column(filter_none([
                ft.Row([
                    file_name_input,
                    file_name_label
                ], alignment=ft.MainAxisAlignment.START),
                run_btn,
                progress_ring,
                result_text,
                md5_text,
                play_indicator if os.name != "nt" else None,
                ft.Row([
                    ft.Column([
                        ft.Text("エンコードWAV", size=12, weight=ft.FontWeight.BOLD),
                        encode_wav_md5_text,
                        ft.Row(filter_none([
                            play_encode_btn,
                            stop_encode_btn if os.name != "nt" else None
                        ]), tight=True)
                    ], spacing=4),
                    ft.Column([
                        ft.Text("ノイズ付加WAV", size=12, weight=ft.FontWeight.BOLD),
                        noise_wav_md5_text,
                        ft.Row(filter_none([
                            play_noise_btn,
                            stop_noise_btn if os.name != "nt" else None
                        ]), tight=True)
                    ], spacing=4)
                ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=24)
            ]), alignment=ft.MainAxisAlignment.START, expand=True)
        ], expand=True),
    )

if __name__ == "__main__":
    # Flet UIをブラウザで開く
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
