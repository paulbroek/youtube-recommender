"""io.methods.py, methods related to IO."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonlines
import pandas as pd
from rarc_utils.decorators import items_per_sec

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
    def load_jsonlines(path: Path) -> pd.DataFrame:
        """Load jsonlines file and parse to dataframe."""
        items: List[Dict[str, Any]] = []
        with jsonlines.open(path) as reader:
            for obj in reader:
                items.append(obj)

        df = pd.DataFrame(items)

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
    def load_feather(df_path: Path, what: Optional[str]) -> pd.DataFrame:
        """Load any dataframe from feather."""
        # check if file exists, or warn user to run main.py first
        assert os.path.exists(df_path), f"{df_path.as_posix()} does not exist"
        assert what is not None
        df: pd.DataFrame = pd.read_feather(df_path)

        WHATS = what + "s" if len(df) != 1 else what
        logger.info(f"loaded {len(df):,} {WHATS} rows from feather")

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
    def load_pickle(df_path: Path, what: Optional[str]) -> pd.DataFrame:
        """Load any dataframe from pickle."""
        # check if file exists, or warn user to run main.py first
        assert os.path.exists(df_path), f"{df_path.as_posix()} does not exist"
        assert what is not None
        df: pd.DataFrame = pd.read_pickle(df_path)

        WHATS = what + "s" if len(df) != 1 else what
        logger.info(f"loaded {len(df):,} {WHATS} rows from pickle")

        return df
