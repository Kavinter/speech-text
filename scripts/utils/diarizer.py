from pathlib import Path
import sherpa_onnx

# Folder for models
MODELS_DIR = Path(__file__).parent.parent / "models"

# Paths to the models
SEGMENTATION_MODEL_PATH = MODELS_DIR / "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
EMBEDDING_MODEL_PATH = MODELS_DIR / "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"

# Function to initialize the segmentation model
def load_segmentation_model():
    model = sherpa_onnx.OnnxModel(SEGMENTATION_MODEL_PATH)
    return model

# Function to initialize the embedding model
def load_embedding_model():
    model = sherpa_onnx.OnnxModel(EMBEDDING_MODEL_PATH)
    return model
