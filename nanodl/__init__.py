from nanodl.__src.sklearn_gpu.bayes import NaiveBayesClassifier
from nanodl.__src.sklearn_gpu.dimensionality_reduction import PCA
from nanodl.__src.sklearn_gpu.clustering import KMeans, GaussianMixtureModel

from nanodl.__src.sklearn_gpu.regression import (
    LinearRegression, 
    LogisticRegression, 
    GaussianProcess
)

from nanodl.__src.models.gat import (
    GAT, 
    GraphAttentionLayer
)

from nanodl.__src.models.t5 import (
    T5,
    T5DataParallelTrainer,
    T5Encoder,
    T5Decoder,
    T5EncoderBlock,
    T5DecoderBlock
)

from nanodl.__src.models.vit import (
    ViT,
    ViTDataParallelTrainer,
    ViTBlock,
    ViTEncoder,
    PatchEmbedding
)

from nanodl.__src.models.clip import (
    CLIP,
    CLIPDataParallelTrainer,
    ImageEncoder,
    TextEncoder,
    SelfMultiHeadAttention
)

from nanodl.__src.models.lamda import (
    LaMDA,
    LaMDADataParallelTrainer,
    LaMDABlock,
    LaMDADecoder,
    RelativeMultiHeadAttention
)

from nanodl.__src.models.mixer import (
    Mixer,
    MixerDataParallelTrainer,
    MixerBlock,
    MixerEncoder
)

from nanodl.__src.models.llama import (
    LlaMA2,
    LlaMADataParallelTrainer,
    RotaryPositionalEncoding,
    LlaMA2Decoder,
    LlaMA2DecoderBlock,
    GroupedRotaryMultiHeadAttention
)

from nanodl.__src.models.gpt import (
    GPT3,
    GPT4,
    GPTDataParallelTrainer,
    GPT3Block,
    GPT4Block,
    GPT3Decoder,
    GPT4Decoder,
    PositionWiseFFN
)

from nanodl.__src.models.mistral import (
    Mistral,
    MistralDataParallelTrainer,
    MistralDecoder,
    MistralDecoderBlock,
    GroupedRotaryShiftedWindowMultiHeadAttention
)

from nanodl.__src.models.mistral import (
    Mixtral,
    MixtralDecoder,
    MixtralDecoderBlock,
    GroupedRotaryShiftedWindowMultiHeadAttention
)

from nanodl.__src.models.whisper import (
    Whisper,
    WhisperDataParallelTrainer,
    WhisperSpeechEncoder,
    WhisperSpeechEncoderBlock
)

from nanodl.__src.models.diffusion import (
    DiffusionModel,
    DiffusionDataParallelTrainer,
    UNet,
    UNetDownBlock,
    UNetUpBlock,
    UNetResidualBlock
)

from nanodl.__src.models.transformer import (
    Transformer,
    TransformerDataParallelTrainer,
    TransformerEncoder,
    TransformerDecoderBlock,
    PositionalEncoding,
    PositionWiseFFN,
    TokenAndPositionEmbedding,
    MultiHeadAttention,
    AddNorm
)

from nanodl.__src.utils.data import (
    Dataset, 
    ArrayDataset, 
    DataLoader
)

from nanodl.__src.utils.ml import (
    batch_cosine_similarities,
    batch_pearsonr,
    classification_scores,
    count_parameters,
    entropy,
    gini_impurity,
    hamming,
    jaccard,
    kl_divergence,
    mean_reciprocal_rank,
    zero_pad_sequences
)

from nanodl.__src.utils.nlp import(
    bleu,
    cider_score,
    meteor,
    perplexity,
    rouge,
    word_error_rate
)

from nanodl.__src.utils.vision import(
    adjust_brightness,
    adjust_contrast,
    flip_image,
    gaussian_blur,
    normalize_images,
    random_crop,
    random_flip_image,
    sobel_edge_detection,
)

__version__ = "0.1.0"

__all__ = [
    # Sklearn GPU
    "NaiveBayesClassifier",
    "PCA",
    "KMeans",
    "GaussianMixtureModel",
    "LinearRegression",
    "LogisticRegression",
    "GaussianProcess",
    
    # Models
    "GAT", 
    "GraphAttentionLayer",
    "T5",
    "T5DataParallelTrainer",
    "T5Encoder",
    "T5Decoder",
    "T5EncoderBlock",
    "T5DecoderBlock",
    "ViT",
    "ViTDataParallelTrainer",
    "ViTBlock",
    "ViTEncoder",
    "PatchEmbedding",
    "CLIP",
    "CLIPDataParallelTrainer",
    "ImageEncoder",
    "TextEncoder",
    "SelfMultiHeadAttention",
    "LaMDA",
    "LaMDADataParallelTrainer",
    "LaMDABlock",
    "LaMDADecoder",
    "RelativeMultiHeadAttention",
    "Mixer",
    "MixerDataParallelTrainer",
    "MixerBlock",
    "MixerEncoder",
    "LlaMA2",
    "LlaMADataParallelTrainer",
    "RotaryPositionalEncoding",
    "LlaMA2Decoder",
    "LlaMA2DecoderBlock",
    "GroupedRotaryMultiHeadAttention",
    "GPT3",
    "GPT4",
    "GPTDataParallelTrainer",
    "GPT3Block",
    "GPT4Block",
    "GPT3Decoder",
    "GPT4Decoder",
    "PositionWiseFFN",
    "Mistral",
    "MistralDataParallelTrainer",
    "MistralDecoder",
    "MistralDecoderBlock",
    "GroupedRotaryShiftedWindowMultiHeadAttention",
    "Mixtral",
    "MixtralDecoder",
    "MixtralDecoderBlock",
    "Whisper",
    "WhisperDataParallelTrainer",
    "WhisperSpeechEncoder",
    "WhisperSpeechEncoderBlock",
    "DiffusionModel",
    "DiffusionDataParallelTrainer",
    "UNet",
    "UNetDownBlock",
    "UNetUpBlock",
    "UNetResidualBlock",
    "Transformer",
    "TransformerDataParallelTrainer",
    "TransformerEncoder",
    "TransformerDecoderBlock",
    "PositionalEncoding",
    "PositionWiseFFN",
    "TokenAndPositionEmbedding",
    "MultiHeadAttention",
    "AddNorm",

    # Utilities
    "Dataset", 
    "ArrayDataset", 
    "DataLoader",
    "batch_cosine_similarities",
    "batch_pearsonr",
    "classification_scores",
    "count_parameters",
    "entropy",
    "gini_impurity",
    "hamming",
    "jaccard",
    "kl_divergence",
    "mean_reciprocal_rank",
    "zero_pad_sequences",
    "bleu",
    "cider_score",
    "meteor",
    "perplexity",
    "rouge",
    "word_error_rate",
    "adjust_brightness",
    "adjust_contrast",
    "flip_image",
    "gaussian_blur",
    "normalize_images",
    "random_crop",
    "random_flip_image",
    "sobel_edge_detection"
]