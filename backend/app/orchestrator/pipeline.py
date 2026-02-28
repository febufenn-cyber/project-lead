from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineConfig:
    run_enrichment: bool = True
    run_scoring: bool = True
    run_deduplication: bool = True


class PipelineManager:
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

    def stages(self) -> list[str]:
        stages = ["scraping"]
        if self.config.run_deduplication:
            stages.append("deduplication")
        if self.config.run_enrichment:
            stages.append("enrichment")
        if self.config.run_scoring:
            stages.append("scoring")
        stages.append("completed")
        return stages
