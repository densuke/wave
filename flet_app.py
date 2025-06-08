import flet as ft
import os
import subprocess
import typing

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
            result_text.value = "ファイル名を入力または選択してください"
            page.update()
            return
        noise_level = int(noise_slider.value)
        bitrate = int(bitrate_slider.value)
        set_noise_level_config(noise_level)
        set_bitrate_config(bitrate)
        # ファイルエンコード
        cmd = ["python3", "encode.py", "--file", orig_file_path, str(noise_level)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=WORK_DIR)
        if result.returncode != 0:
            result_text.value = f"エンコード失敗: {result.stderr}"
            page.update()
            return
        # ノイズ付加
        subprocess.run(["cp", "output.wav", "output_noised.wav"], cwd=WORK_DIR)
        noise_cmd = ["python3", "noise.py", "output_noised.wav", str(noise_level)]
        subprocess.run(noise_cmd, cwd=WORK_DIR)
        # デコード
        decode_cmd = ["python3", "decode.py", "output_noised.wav", "--file", orig_file_path]
        decode_result = subprocess.run(decode_cmd, capture_output=True, text=True, cwd=WORK_DIR)
        # 出力の重複を防ぐため、MD5や[OK]/[NG]部分のみ抽出してmd5_textに、
        # それ以外の復元テキスト部分のみをresult_textに表示
        compare_result = ""
        restored_text = ""
        for line in decode_result.stdout.splitlines():
            if "MD5" in line or "OK" in line or "NG" in line:
                if line not in compare_result:
                    compare_result += line + "\n"
            else:
                restored_text += line + "\n"
        result_text.value = restored_text.strip()
        md5_text.value = compare_result.strip()
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
