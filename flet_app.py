import flet as ft
import os
import typing
# --- 追加: サブプロセス呼び出し不要のためのimport ---
import encode
import noise
import decode
import subprocess  # 再生停止用で必要

# ファイル保存用ディレクトリ
WORK_DIR = os.path.dirname(os.path.abspath(__file__))

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
    config_path = os.path.join(WORK_DIR, "config.toml")
    with open(config_path, "r") as f:
        config_text = f.read()
    bitrate_match = re.search(r"BITRATE\s*=\s*(\d+)", config_text)
    bitrate_init = int(bitrate_match.group(1)) if bitrate_match else 1200

    # ビットレートUI
    bitrate_slider = ft.Slider(min=0, max=9600, divisions=150, label="ビットレート: {value}", value=bitrate_init, width=250)
    bitrate_input = ft.TextField(label="ビットレート(直接入力)", value=str(bitrate_init), width=120, keyboard_type=ft.KeyboardType.NUMBER, on_submit=None, on_change=None)

    def on_bitrate_slider_change(e):
        bitrate_input.value = str(int(bitrate_slider.value))
        page.update()
    def on_bitrate_input_change(e):
        try:
            # 入力が空文字やNoneなら0として扱う
            v = int(bitrate_input.value) if bitrate_input.value is not None and bitrate_input.value != '' else 0
            if 0 <= v <= 9600:
                # 64刻みに補正
                v = (v // 64) * 64
                bitrate_slider.value = v
                bitrate_input.value = str(v)
        except Exception:
            pass
        page.update()
    bitrate_slider.on_change = on_bitrate_slider_change
    bitrate_input.on_submit = on_bitrate_input_change
    bitrate_input.on_change = on_bitrate_input_change

    def set_config_value(key, value):
        with open(config_path, "r") as f:
            lines = f.readlines()
        with open(config_path, "w") as f:
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
        file_path_from_input = file_name_input.value.strip() if file_name_input.value else ""
        if file_path_from_input:
            orig_file_path = file_path_from_input
        if not orig_file_path:
            result_text.value = "ファイル名を入力してください"
            page.update()
            return
        noise_level = int(noise_slider.value)
        bitrate = int(bitrate_slider.value)
        set_noise_level_config(noise_level)
        set_bitrate_config(bitrate)
        # --- ここから内部関数呼び出し ---
        # 1. エンコード: ファイル→output_orig.wav
        bit_string = encode.file_to_bitstring(orig_file_path)
        encode.validate_bit_string(bit_string)
        encode.generate_tone(bit_string, noise_level=noise_level)
        # 2. ノイズ付加: output_orig.wav→output.wav
        import shutil
        shutil.copy2("output_orig.wav", "output.wav")
        with open("output.wav", "rb") as wf:
            import wave
            with wave.open(wf, 'rb') as wavf:
                params = wavf.getparams()
                frames = wavf.readframes(wavf.getnframes())
                samples = noise.np.frombuffer(frames, dtype=noise.np.int16)
        noisy_samples = noise.add_noise(samples, params.framerate, noise_level)
        with wave.open("output.wav", 'wb') as wf:
            wf.setparams(params)
            wf.writeframes(noisy_samples.tobytes())
        # 3. デコード: output.wav→復元結果
        with open(orig_file_path, 'rb') as f:
            orig_bytes = f.read()
        correct_bit_string = ''.join(f'{b:08b}' for b in orig_bytes)
        bit_string_decoded = decode.decode_tone("output.wav", correct_bit_string)
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
        result_text.value = decode.bitstring_to_str(bit_string_decoded)
        # ボタン有効化
        play_encode_btn.disabled = False
        play_noise_btn.disabled = False
        stop_encode_btn.disabled = False
        stop_noise_btn.disabled = False
        page.update()

    run_btn.on_click = on_run

    # 再生停止用
    play_process: dict[str, typing.Any] = {"encode": None, "noise": None}
    def stop_wav(kind):
        proc = play_process.get(kind)
        if proc is not None and hasattr(proc, 'poll') and proc.poll() is None:
            proc.terminate()
        play_process[kind] = None
    def play_wav(path, kind):
        stop_wav(kind)
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

    # レイアウト
    page.add(
        ft.Row([
            ft.Column([
                ft.Text("ノイズレベル", size=14, weight=ft.FontWeight.BOLD),
                noise_slider,
                ft.Text("ビットレート", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([
                    bitrate_slider,
                ], alignment=ft.MainAxisAlignment.START),
                ft.Row([
                    bitrate_input
                ], alignment=ft.MainAxisAlignment.START)
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
                ft.Row([
                    ft.Column([
                        ft.Text("エンコードWAV", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            play_encode_btn,
                            stop_encode_btn
                        ], tight=True)
                    ], spacing=4),
                    ft.Column([
                        ft.Text("ノイズ付加WAV", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            play_noise_btn,
                            stop_noise_btn
                        ], tight=True)
                    ], spacing=4)
                ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=24)
            ], alignment=ft.MainAxisAlignment.START, expand=True)
        ], expand=True),
    )

ft.app(target=main)
