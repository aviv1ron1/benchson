import os
import json


class Dataset:
    def __init__(self, path: str, is_relative: bool = True):
        if is_relative:
            self.path = os.path.join(os.getcwd(), "data", path)
        else:
            self.path = path

        self.train_path = os.path.join(self.path, "train")
        self.test_path = os.path.join(self.path, "test")

        if not os.path.exists(self.path) or not os.path.isdir(self.path):
            raise ValueError(
                f"Dataset path '{self.path}' does not exist or is not a directory."
            )

        if not os.path.exists(self.train_path) or not os.path.isdir(self.train_path):
            # raise ValueError(f"Train folder '{self.train_path}' is missing.")
            print(f"Train folder '{self.train_path}' is missing.")

        if not os.path.exists(self.test_path) or not os.path.isdir(self.test_path):
            raise ValueError(f"Test folder '{self.test_path}' is missing.")

    @classmethod
    def from_json(cls, config_path: str):
        with open(config_path, "r") as f:
            config = json.load(f)
        return cls(config["path"], config.get("is_relative", True))

    def list_train_files(self):
        return [
            f
            for f in os.listdir(self.train_path)
            if os.path.isfile(os.path.join(self.train_path, f))
        ]

    def list_test_files(self):
        return [
            f
            for f in os.listdir(self.test_path)
            if os.path.isfile(os.path.join(self.test_path, f))
        ]

    def iterate_files(self, mode="train"):
        if mode == "train":
            folder = self.train_path
        elif mode == "test":
            folder = self.test_path
        else:
            raise ValueError("Mode must be 'train' or 'test'")

        for file_name in os.listdir(folder):
            file_path = os.path.join(folder, file_name)
            if os.path.isfile(file_path):
                yield file_path

    def __repr__(self):
        return f"Dataset(path='{self.path}', train_files={len(self.list_train_files())}, test_files={len(self.list_test_files())})"
