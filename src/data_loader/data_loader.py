import io
import os
import requests
from itertools import product
from zipfile import ZipFile

import pandas as pd


class HARDataLoader:
    url = "https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip"

    def __init__(self):
        self.df_train_x: pd.DataFrame | None = None
        self.df_train_x_tr: pd.DataFrame | None = None
        self.df_train_y: pd.DataFrame | None = None

        self.df_test_x: pd.DataFrame | None = None
        self.df_test_x_tr: pd.DataFrame | None = None
        self.df_test_y: pd.DataFrame | None = None

    def load(self) -> None:
        """
        Loads the Human Activity Recognition dataset from a specified URL, processes the data, and extracts
        training and testing sets with their respective features and targets.

        Returns
        -------
        None

        Raises
        ------
        requests.RequestException
            If there is an error in making the HTTP request to download the dataset.
        IOError
            If there is an error in reading the zip file or any of its internal files.

        Notes
        -----
        The method performs the following steps:
        1. Downloads the dataset zip file from the provided URL.
        2. Reads the zip file and processes its internal structure.
        3. Extracts the activity labels from the appropriate file.
        4. Extracts training and test data, including specific features and transformed features.
        5. Extracts the target values (activity labels) for both training and test sets.
        """
        # Loading the zip file with the dataset
        response = requests.get(self.url)
        file_bytes = io.BytesIO(response.content)

        # Traversing through the dataset's structure
        data_file = ZipFile(file_bytes, "r")
        data_file = ZipFile(
            io.BytesIO(data_file.read("UCI HAR Dataset.zip")), "r"
        )

        # Getting activity labels
        df_activity_names = pd.read_csv(
            io.BytesIO(data_file.read("UCI HAR Dataset/activity_labels.txt")),
            header=None,
            sep='\s+',
            names=["activity", "name"]
        )

        # Extracting train data
        self.df_train_x = self._make_features(data_file, "train")
        self.df_train_x_tr = self._make_features_tr(data_file, "train")
        self.df_train_y = self._make_targets(
            data_file=data_file,
            df_activity_names=df_activity_names,
            subset="train"
        )

        # Extracting test data
        self.df_test_x = self._make_features(data_file, "test")
        self.df_test_x_tr = self._make_features_tr(data_file, "test")
        self.df_test_y = self._make_targets(
            data_file=data_file,
            df_activity_names=df_activity_names,
            subset="test"
        )

    @staticmethod
    def _make_features(data_file: ZipFile,
                       subset: str) -> pd.DataFrame:
        """
        Makes a DataFrame of raw HAR features (signals).

        Parameters
        ----------
        data_file : ZipFile
            The ZIP file containing the dataset files.

        subset : str
            The subset of data to be processed (e.g., 'train' or 'test').

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the processed features with multi-level index (`signal`, `subject_id`, `timestep`).
        """
        cur_path = os.path.join(
            "UCI HAR Dataset",
            subset
        )

        # Reading subjects
        df_subjects = pd.read_csv(
            io.BytesIO(data_file.read(os.path.join(cur_path, f"subject_{subset}.txt"))),
            header=None,
            sep='\s+',
            names=["subject_id"]
        )

        # Reading signals
        signals_list = ["body_acc", "body_gyro", "total_acc"]
        axes_list = ["x", "y", "z"]

        cur_df_list = []
        for cur_idx in product(signals_list, axes_list):
            cur_signal_name = f"{cur_idx[0]}_{cur_idx[1]}"

            cur_df = pd.read_csv(
                io.BytesIO(data_file.read(
                    os.path.join(cur_path, "Inertial Signals", f"{cur_signal_name}_{subset}.txt"))
                ),
                header=None,
                sep='\s+',
            )

            cur_df.index.name = "sample"
            cur_df["signal"] = cur_signal_name
            cur_df["subject_id"] = df_subjects["subject_id"]
            cur_df = cur_df.set_index(keys=["signal", "subject_id"], append=True)
            cur_df.columns = cur_df.columns.astype(int)
            cur_df_list.append(cur_df)

        df_out = pd.concat(
            cur_df_list,
            ignore_index=False
        )

        df_out.columns.name = "timestep"
        df_out = df_out.unstack(
            "signal"
        ).stack(
            level="timestep",
            future_stack=True
        )

        return df_out

    @staticmethod
    def _make_features_tr(data_file: ZipFile,
                          subset: str) -> pd.DataFrame:
        """
        Makes a DataFrame of HAR features (processed signals).

        Parameters
        ----------
        data_file : ZipFile
            A ZipFile object containing the dataset files.
        subset : str
            The subset of data to be processed (e.g., "train" or "test").

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the processed features with appropriate column names.
        """
        cur_path_names = os.path.join(
            "UCI HAR Dataset",
            f"features.txt"
        )
        df_names = pd.read_csv(
            io.BytesIO(data_file.read(cur_path_names)),
            header=None,
            sep='\s+',
            names=["id", "name"]
        )

        cur_path = os.path.join(
            "UCI HAR Dataset",
            subset,
            f"X_{subset}.txt"
        )

        df_out = pd.read_csv(
            io.BytesIO(data_file.read(cur_path)),
            header=None,
            sep='\s+',
        )

        df_out.rename(columns=df_names["name"].to_dict(), inplace=True)
        df_out.index.name = "sample"

        return df_out

    @staticmethod
    def _make_targets(data_file: ZipFile,
                      df_activity_names: pd.DataFrame,
                      subset: str) -> pd.DataFrame:
        """
        Makes a DataFrame of HAR targets.

        Parameters
        ----------
        data_file : ZipFile
            A zip file object containing the UCI HAR dataset.
        df_activity_names : pd.DataFrame
            A dataframe containing activity names with labels.
        subset : str
            The subset of the dataset to process, typically 'train' or 'test'.
        """
        cur_path = os.path.join(
            "UCI HAR Dataset",
            subset,
            f"y_{subset}.txt"
        )

        df_out = pd.read_csv(
            io.BytesIO(data_file.read(cur_path)),
            header=None,
            sep='\s+',
            names=["label"]
        )
        df_out.index.name = "sample"

        # Adding a column of activity names
        df_out["name"] = df_activity_names.set_index("activity").loc[
            df_out["label"],
            "name"
        ].values

        return df_out
