"""io.methods.py, methods related to IO."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonlines
import pandas as pd
from rarc_utils.decorators import check_file_exists, items_per_sec

logger = logging.getLogger(__name__)


class io_methods:
    """Methods related to IO."""

    @staticmethod
    def reset_jsonlines(path: Path) -> None:
        """Reset jsonlines file."""
        with open(path, "w", encoding="utf"):
            pass

    @staticmethod
    def append_jsonlines(path: Path, items: List[Dict[str, Any]]) -> None:
        """Write intermediary results to jsonlines file."""
        with jsonlines.open(path, mode="a") as writer:
            for item in items:
                writer.write(item)

    @staticmethod
    @check_file_exists
    def load_jsonlines(path: Path) -> pd.DataFrame:
        """Load jsonlines file and parse to dataframe."""
        items: List[Dict[str, Any]] = []
        with jsonlines.open(path) as reader:
            for obj in reader:
                items.append(obj)

        df = pd.DataFrame(items)

        return df

    @staticmethod
    @check_file_exists
    def load_json(path: Path) -> pd.DataFrame:
        """Load json file and parse to dataframe."""
        df: pd.DataFrame = pd.read_json(path)
        logger.info(f"read {len(df):,} lines")

        return df    

    @staticmethod
    def save_feather(
        df: pd.DataFrame, df_path: Path, what: Optional[str] = None
    ) -> None:
        """Save dataframe to feather."""
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df_path, Path)
        assert what is not None

        df.to_feather(df_path)
        WHATS = what + "s" if len(df) != 1 else what
        logger.info(f"saved {len(df):,} {WHATS} to {df_path.as_posix()}")

    @staticmethod
    @check_file_exists
    def load_feather(df_path: Path, what: Optional[str]) -> pd.DataFrame:
        """Load any dataframe from feather."""
        # check if file exists, or warn user to run main.py first
        assert what is not None
        df: pd.DataFrame = pd.read_feather(df_path)

        # WHATS = what + "s" if len(df) != 1 else what
        ROWS = "rows" if len(df) != 1 else "row"
        logger.info(f"loaded {len(df):,} {what} {ROWS} from feather")

        return df

    @staticmethod
    @items_per_sec
    def save_pickle(
        df: pd.DataFrame, df_path: Path, what: Optional[str] = None
    ) -> None:
        """Save dataframe to pickle."""
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df_path, Path)
        assert what is not None

        df.to_pickle(df_path)
        WHATS = what + "s" if len(df) != 1 else what
        logger.info(f"saved {len(df):,} {WHATS} to {df_path.as_posix()}")

    @staticmethod
    @items_per_sec
    @check_file_exists
    def load_pickle(df_path: Path, what: Optional[str]) -> pd.DataFrame:
        """Load any dataframe from pickle."""
        # check if file exists, or warn user to run main.py first
        assert what is not None
        df: pd.DataFrame = pd.read_pickle(df_path)

        WHATS = what + "s" if len(df) != 1 else what
        logger.info(f"loaded {len(df):,} {WHATS} rows from pickle")

        return df

    @classmethod
    def save_topics(cls, topics: List[int], probs: List[float], df_path: Path) -> None:
        """Save topic ids and probabilities to feather."""
        df = pd.DataFrame(dict(topic=topics, prob=probs))
        # df.index.name = 'doc'
        cls.save_feather(df, df_path, what="topic")

    @classmethod
    @check_file_exists
    def load_topics(cls, df_path: Path) -> Tuple[List[int], List[float]]:
        """Load topic ids and probabilities from feather."""
        df = cls.load_feather(df_path, what="topic")

        return df.topic.to_list(), df.prob.to_list()
