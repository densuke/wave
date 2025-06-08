import sys
import os
import importlib
import flet as ft
import subprocess
import typing
import shutil

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
config_template_path = os.path.join(WORK_DIR, "config.toml.in")
config_path = os.path.join(WORK_DIR, "config.toml")
if not os.path.exists(config_path):
    shutil.copy2(config_template_path, config_path)

sys.path.insert(0, os.path.join(WORK_DIR, "lib"))
encode = importlib.import_module("encode")
decode = importlib.import_module("decode")
noise = importlib.import_module("noise")

# config.toml自動生成
config_template_path = os.path.join(WORK_DIR, "config.toml.in")
config_path = os.path.join(WORK_DIR, "config.toml")
if not os.path.exists(config_path):
    shutil.copy2(config_template_path, config_path)

# UIコールバック

def main(page: ft.Page):
    page.title = "FSKエンコード/デコードUI"

    # 入力欄（ファイル名入力のみ、初期値はsample.txt）
    file_name_input = ft.TextField(label="変換元ファイル名（パス）", value="sample.txt", width=400)
    file_name_label = ft.Text(value="", size=12)

    # ノイズレベル
    noise_slider = ft.Slider(min=0, max=5, divisions=5, label="ノイズレベル: {value}", value=0)

    # config.tomlから初期値取得
    import re
    with open(config_path, "r", encoding="utf-8") as f:
        config_text = f.read()
    bitrate_match = re.search(r"BITRATE\s*=\s*(\d+)", config_text)
    bitrate_init = int(bitrate_match.group(1)) if bitrate_match else 1200

    # ビットレート選択肢（8000Hzサンプリングで安全な範囲のみ）
    bitrate_options = [300, 600, 1200, 2400, 4800]  # 9600は除外
    bitrate_dropdown = ft.Dropdown(
        label="ビットレート",
        options=[ft.dropdown.Option(str(b)) for b in bitrate_options],
        value=str(bitrate_init) if bitrate_init in bitrate_options else "1200",
        width=180
    )

    def on_bitrate_dropdown_change(e):
        if bitrate_dropdown.value is not None:
            v = int(bitrate_dropdown.value)
            set_bitrate_config(v)
        page.update()
    bitrate_dropdown.on_change = on_bitrate_dropdown_change

    def set_config_value(key, value):
        with open(config_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(config_path, "w", encoding="utf-8") as f:
            for line in lines:
                if line.strip().startswith(f"{key}"):
                    f.write(f"{key} = {value}\n")
                else:
                    f.write(line)

    def set_noise_level_config(level):
        set_config_value("NOISE_LEVEL", level)
    def set_bitrate_config(bitrate):
        set_config_value("BITRATE", bitrate)

    # 実行ボタン
    run_btn = ft.ElevatedButton("変換開始", disabled=False)

    # 結果表示
    result_text = ft.Text(value="", size=14)
    md5_text = ft.Text(value="", size=14)

    # 音声再生ボタン
    play_encode_btn = ft.ElevatedButton("エンコードWAV再生", disabled=True)
    play_noise_btn = ft.ElevatedButton("ノイズ付加WAV再生", disabled=True)

    # ファイルパス保持
    encode_wav_path = os.path.join(WORK_DIR, "output_orig.wav")  # エンコードWAVはoutput_orig.wav
    noise_wav_path = os.path.join(WORK_DIR, "output.wav")        # ノイズ付加WAVはoutput.wav
    orig_file_path = ""

    def on_run(e):
        # ファイル名取得
        nonlocal orig_file_path
        # Audioウィジェットのsrcを一旦Noneにしてロックを解除
        audio_encode.src = None
        audio_noise.src = None
        page.update()
        # 既存のwavファイルを削除してPermissionErrorを回避
        try:
            if os.path.exists(encode_wav_path):
                os.remove(encode_wav_path)
        except Exception as ex:
            print(f"[警告] {encode_wav_path} の削除に失敗: {ex}")
        try:
            if os.path.exists(noise_wav_path):
                os.remove(noise_wav_path)
        except Exception as ex:
            print(f"[警告] {noise_wav_path} の削除に失敗: {ex}")
        file_path_from_input = file_name_input.value.strip() if file_name_input.value else ""
        if file_path_from_input:
            orig_file_path = file_path_from_input
        if not orig_file_path:
            result_text.value = "ファイル名を入力または選択してください"
            page.update()
            return
        noise_level = int(noise_slider.value)
        bitrate = int(bitrate_dropdown.value) if bitrate_dropdown.value is not None else 1200
        set_noise_level_config(noise_level)
        set_bitrate_config(bitrate)
        # ファイルエンコード
        bit_string = encode.file_to_bitstring(orig_file_path)
        encode.validate_bit_string(bit_string)
        encode.generate_tone(bit_string, duration=1.0/bitrate, sample_rate=8000, noise_level=noise_level, output_path=encode_wav_path)
        # --- output_orig.wav生成直前に個別削除 ---
        try:
            if os.path.exists(encode_wav_path):
                os.remove(encode_wav_path)
        except Exception as ex:
            print(f"[警告] {encode_wav_path} の削除に失敗: {ex}")
        encode.generate_tone(bit_string, duration=1.0/bitrate, sample_rate=8000, noise_level=noise_level, output_path=encode_wav_path)
        # --- output.wav生成直前に既存ファイルをバックアップリネーム ---
        backup_wav_path = noise_wav_path + ".bak"
        if os.path.exists(noise_wav_path):
            try:
                if os.path.exists(backup_wav_path):
                    os.remove(backup_wav_path)
            except Exception as ex:
                print(f"[警告] {backup_wav_path} の削除に失敗: {ex}")
            try:
                os.rename(noise_wav_path, backup_wav_path)
            except Exception as ex:
                print(f"[警告] {noise_wav_path} のリネームに失敗: {ex}")
        # ノイズ付加処理
        shutil.copy2(encode_wav_path, noise_wav_path)
        with open(noise_wav_path, "rb") as wf:
            import wave
            with wave.open(wf, 'rb') as wavf:
                params = wavf.getparams()
                frames = wavf.readframes(wavf.getnframes())
                samples = noise.np.frombuffer(frames, dtype=noise.np.int16)
        noisy_samples = noise.add_noise(samples, 8000, noise_level)
        with wave.open(noise_wav_path, 'wb') as wf:
            wf.setparams(params)
            wf.writeframes(noisy_samples.tobytes())
        # デコード
        with open(orig_file_path, 'rb') as f:
            orig_bytes = f.read()
        correct_bit_string = ''.join(f'{b:08b}' for b in orig_bytes)
        bit_string_decoded = decode.decode_tone(noise_wav_path, correct_bit_string, duration=1.0/bitrate, sample_rate=8000)
        restored_bytes = decode.bitstring_to_bytes(bit_string_decoded)
        import hashlib
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
        page.update()

    run_btn.on_click = on_run

    # 再生停止用
    play_process: dict[str, typing.Any] = {"encode": None, "noise": None}
    # 再生インジケーター
    play_indicator = ft.Text(value="", size=12)
    play_indicator_timer = None
    play_indicator_stop_flag = {"encode": False, "noise": False}

    import time
    import threading
    import wave as pywave

    def format_time(sec):
        m = int(sec) // 60
        s = int(sec) % 60
        return f"{m}:{s:02d}"

    def start_play_indicator(path, kind):
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

    def stop_play_indicator(kind):
        play_indicator_stop_flag[kind] = True

    def stop_wav(kind):
        proc = play_process.get(kind)
        if proc is not None and hasattr(proc, 'poll') and proc.poll() is None:
            proc.terminate()
        play_process[kind] = None
        stop_play_indicator(kind)

    def play_wav(path, kind):
        print(f"[再生] {kind}: {path}")
        stop_wav(kind)
        start_play_indicator(path, kind)
        if os.name == "posix":
            proc = subprocess.Popen(["afplay", path])
        else:
            proc = subprocess.Popen(["start", path], shell=True)
        play_process[kind] = proc

    play_encode_btn.on_click = lambda e: play_wav(encode_wav_path, "encode")
    play_noise_btn.on_click = lambda e: play_wav(noise_wav_path, "noise")
    stop_encode_btn = ft.ElevatedButton("エンコード再生停止", on_click=lambda e: stop_wav("encode"), disabled=True)
    stop_noise_btn = ft.ElevatedButton("ノイズ再生停止", on_click=lambda e: stop_wav("noise"), disabled=True)

    # 再生ボタン有効化時に停止ボタンも有効化
    def enable_play_buttons():
        play_encode_btn.disabled = False
        play_noise_btn.disabled = False
        stop_encode_btn.disabled = False
        stop_noise_btn.disabled = False

    # Audioウィジェットを追加（controls引数を削除）
    audio_encode = ft.Audio(src=encode_wav_path, autoplay=False, volume=1.0)
    audio_noise = ft.Audio(src=noise_wav_path, autoplay=False, volume=1.0)

    def update_audio_src():
        audio_encode.src = encode_wav_path
        audio_noise.src = noise_wav_path
        page.update()

    # 再生ボタンの挙動をAudioウィジェットに変更
    def play_encode_audio(e):
        update_audio_src()
        audio_encode.play()
    def play_noise_audio(e):
        update_audio_src()
        audio_noise.play()
    def stop_encode_audio(e):
        audio_encode.pause()
    def stop_noise_audio(e):
        audio_noise.pause()

    play_encode_btn.on_click = play_encode_audio
    play_noise_btn.on_click = play_noise_audio
    stop_encode_btn = ft.ElevatedButton("エンコード再生停止", on_click=stop_encode_audio, disabled=True)
    stop_noise_btn = ft.ElevatedButton("ノイズ再生停止", on_click=stop_noise_audio, disabled=True)

    # レイアウト
    page.add(
        ft.Row([
            ft.Column([
                ft.Text("ノイズレベル", size=14, weight=ft.FontWeight.BOLD),
                noise_slider,
                ft.Text("ビットレート", size=14, weight=ft.FontWeight.BOLD),
                bitrate_dropdown,
            ], alignment=ft.MainAxisAlignment.START, width=220),
            ft.VerticalDivider(width=1),
            ft.Column([
                ft.Row([
                    file_name_input,
                    file_name_label
                ], alignment=ft.MainAxisAlignment.START),
                run_btn,
                result_text,
                md5_text,
                play_indicator,
                ft.Row([
                    ft.Column([
                        ft.Text("エンコードWAV", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            play_encode_btn,
                            stop_encode_btn,
                            audio_encode
                        ], tight=True)
                    ], spacing=4),
                    ft.Column([
                        ft.Text("ノイズ付加WAV", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            play_noise_btn,
                            stop_noise_btn,
                            audio_noise
                        ], tight=True)
                    ], spacing=4)
                ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=24)
            ], alignment=ft.MainAxisAlignment.START, expand=True)
        ], expand=True),
    )

ft.app(target=main)
