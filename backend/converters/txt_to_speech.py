import os
from .base import BaseConverter
from typing import Dict, Any


class TxtToSpeechConverter(BaseConverter):
    """TXT 到语音转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调支持
    2. 支持 MP3 和 WAV 格式
    3. 使用 gTTS (Google Text-to-Speech) 作为主要引擎
    4. pyttsx3 作为降级方案
    5. 支持多语言
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['mp3', 'wav']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 TXT 转换为语音文件（多策略）"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            if not text.strip():
                raise Exception("文本内容为空")
            
            self.update_progress(input_path, 15)
            
            # 获取选项
            rate = options.get('rate', 150)  # 语速
            volume = options.get('volume', 1.0)  # 音量 0-1
            pitch = options.get('pitch', 1.0)  # 音调 0.5-2.0
            language = options.get('language', 'en')  # 语言代码
            
            print(f"[TTS Options] rate={rate}, volume={volume}, pitch={pitch}, language={language}")
            
            target_format = output_path.split('.')[-1].lower()
            
            # 策略1: 使用 gTTS (推荐,支持 MP3)
            if target_format == 'mp3':
                try:
                    result = self._convert_with_gtts(text, output_path, language, rate, pitch)
                    self.update_progress(input_path, 100)
                    return result
                except Exception as e1:
                    print(f"[gTTS failed] {e1}, trying pyttsx3...")
                    self.update_progress(input_path, 30)
            
            # 策略2: 使用 pyttsx3 (降级方案,主要支持 WAV)
            try:
                result = self._convert_with_pyttsx3(text, output_path, rate, volume, pitch)
                self.update_progress(input_path, 100)
                return result
            except Exception as e2:
                raise Exception(f"All TTS engines failed. gTTS: {str(e1) if target_format == 'mp3' else 'skipped'}, pyttsx3: {str(e2)}")
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to Speech conversion failed: {str(e)}")
    
    def _convert_with_gtts(self, text: str, output_path: str, language: str = 'en', rate: int = 150, pitch: float = 1.0) -> Dict[str, Any]:
        """使用 gTTS 转换（主策略 - 支持 MP3）"""
        try:
            from gtts import gTTS
        except ImportError:
            raise Exception("gTTS not installed. Install with: pip install gtts")
        
        # 语言映射
        lang_map = {
            'en': 'en',
            '英语': 'en',
            'zh': 'zh-CN',
            '中文': 'zh-CN',
            '中文 (普通话)': 'zh-CN',
            'es': 'es',
            '西班牙语': 'es',
            'fr': 'fr',
            '法语': 'fr',
            'de': 'de',
            '德语': 'de'
        }
        
        lang_code = lang_map.get(language, 'en')
        
        # 根据速度调整slow参数
        slow_speech = rate < 120  # 如果速度很慢，使用gTTS的slow模式
        
        print(f"[gTTS] Settings - language: {lang_code}, slow: {slow_speech}, rate: {rate}, pitch: {pitch}")
        
        # 创建 TTS 对象
        tts = gTTS(text=text, lang=lang_code, slow=slow_speech)
        
        # 如果需要调整速度或音调，先保存到临时文件
        if rate != 150 or pitch != 1.0:
            temp_path = output_path + '.temp.mp3'
            tts.save(temp_path)
            
            # 使用音频处理库调整速度和音调
            try:
                self._adjust_audio_properties(temp_path, output_path, rate, pitch)
                # 删除临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as audio_error:
                print(f"[gTTS] Audio adjustment failed: {audio_error}, using original")
                # 如果音频调整失败，使用原始文件
                if os.path.exists(temp_path):
                    os.rename(temp_path, output_path)
        else:
            # 直接保存
            tts.save(output_path)
        
        if not os.path.exists(output_path):
            raise Exception("Audio file generation failed")
        
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'method': 'gtts',
            'language': lang_code,
            'settings': {
                'rate': rate,
                'pitch': pitch,
                'slow_mode': slow_speech
            }
        }
    
    def _convert_with_pyttsx3(self, text: str, output_path: str, rate: int = 150, volume: float = 1.0, pitch: float = 1.0) -> Dict[str, Any]:
        """使用 pyttsx3 转换（降级方案 - 主要支持 WAV）"""
        try:
            import pyttsx3
        except ImportError:
            raise Exception("pyttsx3 not installed. Install with: pip install pyttsx3")
        
        engine = pyttsx3.init()
        
        # 配置语音参数
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)
        
        # 尝试设置音调（不是所有TTS引擎都支持）
        try:
            voices = engine.getProperty('voices')
            if voices:
                # 选择合适的语音
                current_voice = engine.getProperty('voice')
                print(f"[pyttsx3] Current voice: {current_voice}")
                print(f"[pyttsx3] Available voices: {len(voices)}")
                
                # 如果有多个语音可选，可以根据pitch选择不同的语音
                if len(voices) > 1 and pitch != 1.0:
                    # 简单的音调映射：高音调选择女声，低音调选择男声
                    if pitch > 1.2:
                        # 寻找女声
                        for voice in voices:
                            if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                                engine.setProperty('voice', voice.id)
                                break
                    elif pitch < 0.8:
                        # 寻找男声
                        for voice in voices:
                            if 'male' in voice.name.lower() or 'man' in voice.name.lower():
                                engine.setProperty('voice', voice.id)
                                break
        except Exception as voice_error:
            print(f"[pyttsx3] Voice adjustment failed: {voice_error}")
        
        print(f"[pyttsx3] Final settings - rate: {rate}, volume: {volume}, pitch: {pitch}")
        
        # 保存为音频文件
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        if not os.path.exists(output_path):
            raise Exception("Audio file generation failed")
        
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'method': 'pyttsx3',
            'settings': {
                'rate': rate,
                'volume': volume,
                'pitch': pitch
            }
        }
    def _adjust_audio_properties(self, input_path: str, output_path: str, rate: int, pitch: float):
        """调整音频的速度和音调"""
        try:
            # 尝试使用 pydub 进行音频处理
            from pydub import AudioSegment
            from pydub.effects import speedup
            
            # 加载音频
            audio = AudioSegment.from_mp3(input_path)
            
            # 计算速度倍率 (基准速度150)
            speed_ratio = rate / 150.0
            
            # 调整速度
            if speed_ratio != 1.0:
                if speed_ratio > 1.0:
                    # 加速
                    audio = speedup(audio, playback_speed=speed_ratio)
                else:
                    # 减速 - 通过重复采样实现
                    new_sample_rate = int(audio.frame_rate * speed_ratio)
                    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
                    audio = audio.set_frame_rate(audio.frame_rate)
            
            # 调整音调 (通过改变采样率实现简单的音调调整)
            if pitch != 1.0:
                new_sample_rate = int(audio.frame_rate * pitch)
                audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
                audio = audio.set_frame_rate(44100)  # 标准化到44.1kHz
            
            # 导出调整后的音频
            audio.export(output_path, format="mp3")
            
        except ImportError:
            print("[Audio Processing] pydub not available, trying alternative method")
            # 如果pydub不可用，尝试使用ffmpeg (如果可用)
            self._adjust_audio_with_ffmpeg(input_path, output_path, rate, pitch)
        except Exception as e:
            print(f"[Audio Processing] Failed: {e}")
            raise e
    
    def _adjust_audio_with_ffmpeg(self, input_path: str, output_path: str, rate: int, pitch: float):
        """使用ffmpeg调整音频属性"""
        import subprocess
        
        # 计算速度倍率
        speed_ratio = rate / 150.0
        
        # 构建ffmpeg命令
        cmd = ['ffmpeg', '-i', input_path, '-y']
        
        # 音频滤镜
        filters = []
        
        if speed_ratio != 1.0:
            filters.append(f'atempo={speed_ratio}')
        
        if pitch != 1.0:
            # 使用asetrate和aresample来调整音调
            filters.append(f'asetrate=44100*{pitch},aresample=44100')
        
        if filters:
            cmd.extend(['-af', ','.join(filters)])
        
        cmd.append(output_path)
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"[ffmpeg] Failed: {e}")
            # 如果ffmpeg也失败，直接复制原文件
            import shutil
            shutil.copy2(input_path, output_path)