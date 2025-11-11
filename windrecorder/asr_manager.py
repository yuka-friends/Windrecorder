"""
ASR (Automatic Speech Recognition) Manager
自动语音识别管理器，负责音频转文字的核心逻辑
"""

import os
import gc
import time
from typing import Dict, List, Optional

# 在导入任何其他模块之前，先设置环境变量禁用 FunASR 的自动更新检查
# 这样可以防止网络问题导致导入时卡顿
os.environ.setdefault("MODELSCOPE_CACHE", os.path.expanduser("~/.cache/modelscope"))
os.environ["MODELSCOPE_MODULES_CACHE"] = os.path.expanduser("~/.cache/modelscope/hub")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from windrecorder.config import config
from windrecorder.logger import get_logger

logger = get_logger(__name__)


class ASRManager:
    """ASR 管理类，处理音频转文字任务"""

    def __init__(self):
        self.model = None
        self.vad_model = None
        self._model_loaded = False

    def _load_sensevoice_model(self):
        """懒加载 SenseVoice 模型"""
        try:
            if self._model_loaded:
                logger.debug("Model already loaded, skipping")
                return

            # 检查可用内存
            if HAS_PSUTIL:
                try:
                    mem = psutil.virtual_memory()
                    available_gb = mem.available / (1024 ** 3)
                    logger.info(f"Available memory: {available_gb:.2f} GB ({mem.percent}% used)")

                    # 如果可用内存小于 2GB，尝试清理内存
                    if available_gb < 2.0:
                        logger.warning(f"Low memory detected ({available_gb:.2f} GB available). Attempting garbage collection...")
                        gc.collect()
                        mem = psutil.virtual_memory()
                        available_gb = mem.available / (1024 ** 3)
                        logger.info(f"Memory after GC: {available_gb:.2f} GB available")

                        if available_gb < 1.5:
                            logger.error(
                                f"Insufficient memory to load ASR model. "
                                f"Available: {available_gb:.2f} GB, Required: ~2-3 GB. "
                                f"Please close some applications and try again."
                            )
                            self._model_loaded = False
                            return
                except Exception as e:
                    logger.warning(f"Could not check memory status: {e}")
            else:
                logger.debug("psutil not available, skipping memory check")

            logger.info(f"Attempting to load SenseVoice model from: {config.asr_model_dir}")

            # 禁用 FunASR 的自动更新检查（防止网络问题导致卡顿）
            os.environ.setdefault("MODELSCOPE_CACHE", os.path.expanduser("~/.cache/modelscope"))
            os.environ["FUNASR_DISABLE_UPDATE_CHECK"] = "1"

            logger.debug("Importing FunASR AutoModel (this may take 2-5 minutes on first load)...")
            import_start = time.time()
            from funasr import AutoModel
            import_elapsed = time.time() - import_start
            logger.debug(f"FunASR AutoModel imported successfully in {import_elapsed:.2f}s")

            logger.info(f"Loading SenseVoice model: {config.asr_model_dir}")
            logger.info("NOTE: First-time model loading may take 5-10 minutes to download ~900MB model file")
            logger.info("Please be patient, the download progress will be logged below...")

            # 确定设备
            device = "cuda:0" if config.asr_use_gpu else "cpu"
            logger.info(f"ASR device: {device}")

            # 加载模型
            self.model = AutoModel(
                model=config.asr_model_dir,
                trust_remote_code=True,
                disable_update=True,  # 禁用自动更新检查，避免网络问题导致卡顿
                vad_model="fsmn-vad",  # 启用 VAD 进行长音频切割
                vad_kwargs={"max_single_segment_time": 30000},  # 最大切割时长 30 秒
                device=device,
            )

            self._model_loaded = True
            logger.info("SenseVoice model loaded successfully")

        except ImportError as e:
            logger.error(f"Failed to import FunASR: {e}", exc_info=True)
            logger.error("Please install FunASR: pip install funasr")
            self._model_loaded = False
        except OSError as e:
            # 处理内存不足或 DLL 加载失败的问题
            error_msg = str(e)
            if "WinError 8" in error_msg or "存储空间不足" in error_msg or "c10.dll" in error_msg:
                logger.error(
                    "Failed to load ASR model due to insufficient memory. "
                    "This error typically occurs when:\n"
                    "  1. System memory is low (< 2GB available)\n"
                    "  2. Too many applications are running\n"
                    "  3. WebUI is consuming significant memory\n"
                    "Solutions:\n"
                    "  - Close some applications to free up memory\n"
                    "  - Restart the WebUI\n"
                    "  - Consider upgrading system RAM\n"
                    f"Error details: {e}",
                    exc_info=True
                )
            elif "WinError 206" in error_msg or "文件名或扩展名太长" in error_msg or "filename or extension is too long" in error_msg:
                logger.error(
                    "Failed to load ASR model due to Windows path length limitation. "
                    "This error occurs because the virtual environment path is too long.\n"
                    "Solutions:\n"
                    "  1. Enable Windows Long Path Support:\n"
                    "     - Run as Administrator: reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f\n"
                    "     - Or: Open Group Policy Editor → Computer Configuration → Administrative Templates → System → Filesystem → Enable Win32 long paths\n"
                    "  2. Move the project to a shorter path (e.g., C:\\Windrecorder)\n"
                    "  3. Recreate virtual environment with shorter name\n"
                    f"Current path length: {len(str(e))} characters\n"
                    f"Error details: {e}",
                    exc_info=True
                )
            else:
                logger.error(f"OSError while loading SenseVoice model: {e}", exc_info=True)
            self._model_loaded = False
        except Exception as e:
            logger.error(f"Failed to load SenseVoice model: {e}", exc_info=True)
            self._model_loaded = False

    def is_available(self) -> bool:
        """检查 ASR 是否可用"""
        if not config.enable_audio_asr:
            return False

        if config.asr_engine != "sensevoice":
            logger.warning(f"Unsupported ASR engine: {config.asr_engine}")
            return False

        # 尝试加载模型
        if not self._model_loaded:
            logger.info("ASR model not loaded yet, attempting to load...")
            self._load_sensevoice_model()

        return self._model_loaded

    def transcribe_audio(self, audio_path: str, audio_type: str = "system") -> Dict:
        """
        转录音频文件为文字

        Args:
            audio_path: 音频文件路径
            audio_type: 音频类型，'system' 或 'mic'

        Returns:
            dict: {
                'text': 转录文本,
                'raw_text': 原始转录文本（未过滤）,
                'timestamps': 时间戳列表,
                'language': 检测到的语言,
                'emotion': 情感标签（如果有）
            }
        """
        logger.info(f"goto asr : {audio_path} (type: {audio_type})")
        if not self.is_available():
            logger.error("ASR is not available")
            return self._empty_result()

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return self._empty_result()

        try:
            logger.info(f"Transcribing audio: {audio_path} (type: {audio_type})")

            # 执行 ASR
            result = self.model.generate(
                input=audio_path,
                cache={},
                language=config.asr_language,  # "auto", "zh", "en", "yue", "ja", "ko"
                use_itn=config.asr_use_itn,  # 是否使用逆文本正则化（标点等）
                ban_emo_unk=config.asr_ban_emo_unk,  # 禁用emo_unk标签，所有句子赋予情感标签
                batch_size_s=config.asr_batch_size_s,  # 动态 batch，总音频时长（秒）
                merge_vad=config.asr_merge_vad,  # 是否合并 VAD 切割的音频碎片
                merge_length_s=config.asr_merge_length_s,  # 合并后的长度（秒）
            )

            if not result or len(result) == 0:
                logger.warning(f"No ASR result for: {audio_path}")
                return self._empty_result()

            # 提取结果
            raw_text = result[0].get("text", "")
            timestamps = result[0].get("timestamp", [])
            language = result[0].get("language", "unknown")

            # 后处理文本
            filtered_text = self._postprocess_text(raw_text, audio_type)

            logger.info(
                f"ASR completed: {audio_path} | Raw length: {len(raw_text)} | Filtered length: {len(filtered_text)}"
            )

            return {
                "text": filtered_text,
                "raw_text": raw_text,
                "timestamps": timestamps,
                "language": language,
                "emotion": result[0].get("emotion", None),
            }

        except Exception as e:
            logger.error(f"ASR transcription failed for {audio_path}: {e}", exc_info=True)
            return self._empty_result()

    def _postprocess_text(self, text: str, audio_type: str) -> str:
        """
        文本后处理：过滤噪音、音乐等

        Args:
            text: 原始转录文本
            audio_type: 音频类型 ('system' 或 'mic')

        Returns:
            str: 过滤后的文本
        """
        if not text:
            return ""

        # 1. 移除过短文本（可能是噪音）
        if len(text.strip()) < config.asr_min_text_length:
            logger.debug(f"Text too short, filtered: {text[:50]}")
            return ""

        # 2. 检测重复模式（歌词特征）
        if self._is_repetitive(text):
            logger.debug(f"Repetitive text detected (music?), filtered: {text[:50]}")
            return ""

        # 3. 过滤音乐关键词（针对系统音频）
        if audio_type == "system" and config.asr_music_filter_keywords:
            for keyword in config.asr_music_filter_keywords:
                if keyword.lower() in text.lower():
                    logger.debug(f"Music keyword detected, filtered: {text[:50]}")
                    return ""

        return text.strip()

    def _is_repetitive(self, text: str) -> bool:
        """
        检测文本是否重复（歌词特征）

        Args:
            text: 待检测文本

        Returns:
            bool: 是否重复
        """
        words = text.split()
        if len(words) < 10:
            return False

        # 计算唯一词比例
        unique_ratio = len(set(words)) / len(words)
        is_repetitive = unique_ratio < config.asr_repetitive_threshold

        if is_repetitive:
            logger.debug(f"Repetitive ratio: {unique_ratio:.2f} < {config.asr_repetitive_threshold}")

        return is_repetitive

    def _empty_result(self) -> Dict:
        """返回空结果"""
        return {
            "text": "",
            "raw_text": "",
            "timestamps": [],
            "language": "unknown",
            "emotion": None,
        }

    def process_pending_audio_files(self, batch_size: Optional[int] = None):
        """
        批量处理未转录的音频文件（在闲时维护中调用）

        Args:
            batch_size: 批量处理大小，None 则使用配置值
        """
        if not self.is_available():
            logger.warning("ASR is not available, skipping audio processing")
            return

        if batch_size is None:
            batch_size = config.batch_size_asr_in_idle

        logger.info(f"Starting ASR batch processing (batch_size={batch_size})")

        try:
            from windrecorder.db_manager import db_manager

            # 查询未处理的音频文件
            pending_audios = db_manager.db_get_pending_asr_audiofiles(limit=batch_size)

            if not pending_audios:
                logger.info("No pending audio files for ASR")
                return

            logger.info(f"Found {len(pending_audios)} audio files to process")

            # 逐个处理
            for idx, audio_info in enumerate(pending_audios, 1):
                audio_filename = audio_info["audiofile_name"]
                audio_type = audio_info["audio_type"]
                audio_path = audio_info["audio_path"]

                logger.info(f"Processing [{idx}/{len(pending_audios)}]: {audio_filename}")

                # 检查文件是否存在
                if not os.path.exists(audio_path):
                    logger.warning(f"Audio file not found: {audio_path}")
                    # 标记为已处理（避免重复查询）
                    db_manager.db_mark_audio_asr_indexed(audio_filename, success=False)
                    continue

                # 执行 ASR
                result = self.transcribe_audio(audio_path, audio_type)

                # 更新数据库
                if result["text"]:
                    db_manager.db_update_asr_text(
                        audiofile_name=audio_filename,
                        asr_text=result["text"],
                        asr_language=result["language"],
                        audio_source=1 if audio_type == "system" else 2,
                    )
                    logger.info(f"ASR text saved: {audio_filename} | Length: {len(result['text'])}")
                else:
                    logger.info(f"No valid text extracted: {audio_filename}")

                # 标记已处理
                db_manager.db_mark_audio_asr_indexed(audio_filename, success=True)

            logger.info(f"ASR batch processing completed: {len(pending_audios)} files")

        except Exception as e:
            logger.error(f"Error in ASR batch processing: {e}", exc_info=True)

    def cleanup_old_audio_files(self):
        """清理过期的音频文件（保留 ASR 文本）"""
        if config.asr_auto_delete_audio_days <= 0:
            return

        logger.info(f"Cleaning up audio files older than {config.asr_auto_delete_audio_days} days")

        try:
            from windrecorder.db_manager import db_manager
            import datetime

            # 计算截止日期
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=config.asr_auto_delete_audio_days)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")

            # 查询需要删除的音频文件
            old_audios = db_manager.db_get_old_audio_files(cutoff_date=cutoff_str)

            if not old_audios:
                logger.info("No old audio files to delete")
                return

            logger.info(f"Found {len(old_audios)} audio files to delete")

            deleted_count = 0
            for audio_info in old_audios:
                audio_path = audio_info["audio_path"]

                if os.path.exists(audio_path):
                    try:
                        if config.recycle_deleted_files:
                            from send2trash import send2trash

                            send2trash(audio_path)
                        else:
                            os.remove(audio_path)

                        deleted_count += 1
                        logger.info(f"Deleted audio file: {audio_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete audio file {audio_path}: {e}")

            logger.info(f"Audio cleanup completed: {deleted_count}/{len(old_audios)} files deleted")

        except Exception as e:
            logger.error(f"Error in audio cleanup: {e}", exc_info=True)


# 全局单例
asr_manager = ASRManager()
