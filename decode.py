from lib.utils import read_wav_file, calculate_fft
import toml
import sys
import numpy as np
# 設定を読み込む
config = toml.load("config.toml")
DURATION = config["DURATION"]
SAMPLE_RATE = config["SAMPLE_RATE"]

def decode_tone(file_path, correct_bit_string=None, duration=DURATION, sample_rate=SAMPLE_RATE):
    """
    WAVファイルを読み取り、0と1の文字列を復元する。

    :param file_path: 入力WAVファイルのパス
    :param correct_bit_string: 正解のビット列（オプション）
    :param duration: 各音の長さ（秒）
    :param sample_rate: サンプリングレート
    """
    # 削除: 未使用の変数
    # freq_map = {440: '0', 880: '1'}
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

        # 周波数範囲を制限（期待される周波数の近傍のみを検出）
        valid_indices = np.where((freqs >= 300) & (freqs <= 1000))  # 300Hz〜1000Hzの範囲
        valid_freqs = freqs[valid_indices]
        valid_magnitude = magnitude[valid_indices]

        # 有効範囲内で最大振幅を持つ周波数を取得
        if len(valid_freqs) > 0:
            peak_freq = valid_freqs[np.argmax(valid_magnitude)]
        else:
            peak_freq = 0  # 有効な周波数が見つからない場合

        # 平均周波数を基に判定
        print(f"Segment {i // samples_per_tone}: Filtered Peak Frequency = {peak_freq:.2f} Hz")
        if abs(peak_freq - 440) < abs(peak_freq - 880):
            bit_string += '0'
            print('0')
        else:
            bit_string += '1'
            print('1')

    # 結果を表示
    print("復元された文字列:")
    print(bit_string)

    if correct_bit_string:
        print("正解の文字列:")
        print(correct_bit_string)

        # 縦に並べて比較
        print("比較:")
        for decoded, correct in zip(bit_string, correct_bit_string):
            print(f"{decoded} | {correct}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("使い方: python3 decode.py <WAVファイルパス> [正解のビット列]")
        sys.exit(1)

    file_path = sys.argv[1]
    correct_bit_string = sys.argv[2] if len(sys.argv) == 3 else None

    decode_tone(file_path, correct_bit_string)