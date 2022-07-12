import pandas as pd


class comments_methods:
    @staticmethod
    def parse_votes(df):
        """Parse votes of comments.

        For likes > 1_000, it displays as:
            1.3K
            2.6K
        """
        assert "votes" in df
        if str(df.votes.dtype) != "object":
            return df

        df["votes_isdigit"] = df.votes.map(lambda x: x.isdigit())
        if not df.votes_isdigit.all():

            # ends_with_k = df.votes.str.endswith('K')
            # df.loc[np.where(ends_with_k), "votes"] = ends_with_k, df[ends_with_k].votes.str.replace('K','').astype(float) * 1_000
            df["votes"] = df.votes.apply(
                lambda x: float(x.replace("K", "")) * 1_000 if x.endswith("K") else x
            )

        # df["votes_isdigit"] = df.votes.map(lambda x: x.isdigit())
        # assert df.votes_isdigit.all()
        df["votes"] = df.votes.astype(int)

        return df

    @classmethod
    def comments_pipeline(cls, df):
        df = cls.parse_votes(df)
        df["time_parsed_float"] = df["time_parsed"]
        df["time_parsed"] = pd.to_datetime(
            df.time_parsed_float * 1_000, unit="ms"
        ).astype("datetime64[us]")
        return df
