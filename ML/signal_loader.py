import os
import re
import numpy as np


class ADCDataset:

    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir
        self.files = []

    def scan(self):

        txt_files = []

        for file in os.listdir(self.dataset_dir):

            if file.endswith(".txt"):

                full_path = os.path.join(
                    self.dataset_dir,
                    file
                )

                freq = self.extract_frequency(file)

                txt_files.append({
                    "file": file,
                    "path": full_path,
                    "frequency": freq
                })

        txt_files.sort(
            key=lambda x: x["frequency"]
        )

        self.files = txt_files

        return txt_files

    @staticmethod
    def extract_frequency(filename):

        match = re.search(
            r'20hz(\d+)\.txt',
            filename
        )

        if match:
            return int(match.group(1))

        return -1

    @staticmethod
    def load_adc_file(filepath):

        values = []

        with open(filepath, "r") as f:

            for line in f:

                line = line.strip()

                if line.startswith("ADC:"):

                    values.append(
                        int(
                            line.split(":")[1]
                        )
                    )

        return np.array(
            values,
            dtype=np.float32
        )