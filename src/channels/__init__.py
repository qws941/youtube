"""Channel-specific pipelines."""
from src.channels.facts import FactsPipeline
from src.channels.finance import FinancePipeline
from src.channels.horror import HorrorPipeline

__all__ = [
    "HorrorPipeline",
    "FactsPipeline",
    "FinancePipeline",
]
