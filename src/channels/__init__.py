"""Channel-specific pipelines."""
from src.channels.horror import HorrorPipeline
from src.channels.facts import FactsPipeline
from src.channels.finance import FinancePipeline

__all__ = [
    "HorrorPipeline",
    "FactsPipeline",
    "FinancePipeline",
]
