from lib.utils import read_wav_file, calculate_fft
import toml
import io
import numpy as np
import argparse
import hashlib
from typing import Optional

# 設定を読み込む（Windows対応: encoding指定）
def load_config_toml(config_path: str = "config.toml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return toml.load(io.StringIO(f.read()))

config = load_config_toml()
SAMPLE_RATE: int = config["SAMPLE_RATE"]
BITRATE: int = config["BITRATE"]  # 1秒間に何ビット詰め込むか

def decode_tone(
    file_path: str,
    correct_bit_string: Optional[str] = None,
    duration: Optional[float] = None,
    sample_rate: int = SAMPLE_RATE
) -> str:
    """
    WAVファイルを読み取り、0と1の文字列を復元する。

    :param file_path: 入力WAVファイルのパス
    :param correct_bit_string: 正解のビット列（オプション）
    :param duration: 各音の長さ（秒）
    :param sample_rate: サンプリングレート
    """
    if duration is None:
        duration = 1.0 / BITRATE  # 1ビットあたりの秒数

    # 削除: 未使用の変数
    # freq_map = {440: '0', 880: '1'}
    #freq_map = {1200: '0', 2200: '1'}  # Bell 202 FSK
    # threshold = 100

    # WAVファイルを読み取る
    samples = read_wav_file(file_path)

    # 各セグメントの周波数を計算
    bit_string = ""
    samples_per_tone = int(sample_rate * duration)
    for i in range(0, len(samples), samples_per_tone):
        segment = samples[i:i + samples_per_tone]
        # 最後のセグメントが短い場合でも処理する
        if len(segment) < samples_per_tone:
            print(f"Warning: Segment {i // samples_per_tone} is shorter than expected.")

        # 区間内の平均周波数を計算
        freqs, magnitude = calculate_fft(segment, sample_rate)

        # 周波数範囲を制限（Bell 202: 1000Hz〜2500Hzの範囲）
        valid_indices = np.where((freqs >= 1000) & (freqs <= 2500))
        valid_freqs = freqs[valid_indices]
        valid_magnitude = magnitude[valid_indices]

        # 有効範囲内で最大振幅を持つ周波数を取得
        if len(valid_freqs) > 0:
            peak_freq = valid_freqs[np.argmax(valid_magnitude)]
        else:
            peak_freq = 0  # 有効な周波数が見つからない場合

        # FSK判定（1200Hz/2200Hz）
        # print(f"Segment {i // samples_per_tone}: Filtered Peak Frequency = {peak_freq:.2f} Hz")
        if abs(peak_freq - 1200) < abs(peak_freq - 2200):
            bit_string += '0'
            # print('0')
        else:
            bit_string += '1'
            # print('1')

    # 結果を表示
    # print("復元された文字列:")
    # print(bit_string)
    #print("復元されたテキスト:")
    #print(bitstring_to_str(bit_string))

    # if correct_bit_string:
    #     print("正解の文字列:")
    #     print(correct_bit_string)
    return bit_string


def bitstring_to_str(bit_string: str) -> str:
    # 8ビットごとに区切ってバイト列に変換し、UTF-8デコード
    bytes_list = [bit_string[i:i+8] for i in range(0, len(bit_string), 8)]
    byte_values = [int(b, 2) for b in bytes_list if len(b) == 8]
    try:
        return bytes(byte_values).decode('utf-8')
    except Exception as e:
        return f"[デコード失敗: {e}]"

def bitstring_to_bytes(bit_string: str) -> bytes:
    bytes_list = [bit_string[i:i+8] for i in range(0, len(bit_string), 8)]
    byte_values = [int(b, 2) for b in bytes_list if len(b) == 8]
    return bytes(byte_values)

def main() -> None:
    parser = argparse.ArgumentParser(description="FSK音声からビット列・文字列・ファイルを復元")
    parser.add_argument('input', help='デコードするWAVファイル')
    parser.add_argument('--file', type=str, help='元データファイル（MD5比較用）')
    args = parser.parse_args()

    file_path = args.input
    correct_bit_string = None
    orig_bytes = None
    orig_md5 = None
    if args.file:
        with open(args.file, 'rb') as f:
            orig_bytes = f.read()
            orig_md5 = hashlib.md5(orig_bytes).hexdigest()
        correct_bit_string = ''.join(f'{b:08b}' for b in orig_bytes)

    bit_string = decode_tone(file_path, correct_bit_string)
    restored_bytes = bitstring_to_bytes(bit_string)
    if args.file:
        restored_md5 = hashlib.md5(restored_bytes).hexdigest()
        print(f"[MD5] 元データ: {orig_md5}")
        print(f"[MD5] 復元データ: {restored_md5}")
        if orig_md5 == restored_md5:
            print("[OK] MD5一致: 完全復元")
        else:
            print("[NG] MD5不一致: データ化けあり")

if __name__ == "__main__":
    main()
