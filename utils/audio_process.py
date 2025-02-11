from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import torch
import logging

logger = logging.getLogger('Muice.SpeechRecognition')

class SpeechRecognitionPipeline:
    _model = None

    @classmethod
    def load_model(cls, model_path):
        logger.info("Loading speech recognition model...")
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        logger.info("Using device: {}".format(device))
        try:
            cls._model = AutoModel(
                                   model=model_path,
                                   trust_remote_code=False,
                                   device=str(device),
                                   disable_update=True
                                   )
        except Exception as e:
            if "Loading remote code failed: model, No module named 'model'" in str(e):
                try:
                    cls._model = AutoModel(
                                           model=model_path,
                                           trust_remote_code=False,
                                           device=str(device),
                                           disable_update=True
                                           )
                except Exception as e2:
                    logger.error("Failed to load speech recognition model: {}".format(e2))
                    raise e2 from e
            else:
                logger.error("Failed to load speech recognition model: {}".format(e))
                raise e
        logger.info("Model loaded successfully.")

    async def generate_speech(self, file_path):
        logger.info("Generating speech...")
        rec_result = self._model.generate(
                                          input=file_path,
                                          cache={},
                                          language="zh", # "auto", "zh", "en", "yue", "ja", "ko", "nospeech"
                                          batch_size_s=60,
                                          merge_vad=True,
                                          merge_length_s=15
                                          )
        rec_result = rich_transcription_postprocess(rec_result[0]["text"])
        logger.info(f"Speech generated : {rec_result}")
        return rec_result