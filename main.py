import wave
import struct
import math

def generate_tone(bit_string, duration=1.0, sample_rate=44100):
    """
    0と1の文字列から、それぞれ440Hzと880Hzの音を生成し、WAVファイルに保存する。

    :param bit_string: 0と1の並んだ文字列
    :param duration: 各音の長さ（秒）
    :param sample_rate: サンプリングレート
    """
    # 周波数のマッピング
    freq_map = {'0': 440, '1': 880}

    # WAVファイルの設定
    output_file = "output.wav"
    amplitude = 32767  # 最大振幅（16ビットPCM）

    # サンプルデータを格納するリスト
    samples = []

    for bit in bit_string:
        if bit not in freq_map:
            print(f"無効な文字: {bit}（スキップします）")
            continue

        frequency = freq_map[bit]
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = amplitude * math.sin(2 * math.pi * frequency * t)
            samples.append(int(sample))

    # WAVファイルの書き込み
    with wave.open(output_file, 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16ビット
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))

    print(f"WAVファイルを生成しました: {output_file}")

if __name__ == "__main__":
    # 例: 0と1の並んだ文字列
    bit_string = "01010110"
    generate_tone(bit_string)
