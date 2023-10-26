import shutil
from pathlib import Path

import pandas as pd
from arosics import COREG
import numpy as np

def coregister(
    output_dir,
    sitename,
    foldersite,
    satellite,
    max_shift=100,
    backup_suffix="_backup",
    remove_backup=False,
):
    root = f"{output_dir}/{sitename}/{foldersite}/{satellite}"
    backup = f"{root}{backup_suffix}"

    meta_folder = "meta"
    meta_ext = ".txt"
    image_ext = ".tif"

    img_folders = []
    if satellite == "L7" or satellite == "L8":
        img_folders = ["ms", "pan"]
    elif satellite == "L5":
        img_folders = ["30m"]
    elif satellite == "S2":
        img_folders = ["10m", "20m", "60m"]

    shutil.move(root, backup)
    Path(root).mkdir(exist_ok=True)

    meta_files = sorted(Path(f"{backup}/{meta_folder}").glob(f"*{meta_ext}"))
    Path(f"{root}/{meta_folder}").mkdir(parents=True, exist_ok=True)

    dfs_meta = []
    for meta_file in meta_files:
        df = pd.read_csv(meta_file, delim_whitespace=True, header=None, index_col=0).T
        # Transposing a DataFrame with mixed dtypes will result in a homogeneous
        # DataFrame with the object dtype
        df["acc_georef"] = pd.to_numeric(df["acc_georef"])
        dfs_meta.append(df)

    df_meta = pd.concat(dfs_meta, ignore_index=True).set_index("filename")

    image_suffix = image_ext
    if satellite == "L7" or satellite == "L8":
        image_suffix = "_pan" + image_suffix
    elif satellite == "S2":
        image_suffix = "_10m" + image_suffix

    reference_file = df_meta["acc_georef"].idxmin().replace(image_suffix, "")

    image_files = sorted([i.replace(image_suffix, "") for i in df_meta.index.to_list()])
    image_files.remove(reference_file)

    for img_folder in img_folders:
        Path(f"{root}/{img_folder}").mkdir(parents=True, exist_ok=True)

    total_coregistered = 0
    for image_file in image_files:
        for img_folder in img_folders:
            if satellite == "L7" or satellite == "L8" or satellite == "S2":
                folder_suffix = f"_{img_folder}"
            else:
                folder_suffix = ""

            try:
                np.seterr(divide='ignore', invalid='ignore')
                CR = COREG(
                    f"{backup}/{img_folder}/{reference_file}{folder_suffix}{image_ext}",
                    f"{backup}/{img_folder}/{image_file}{folder_suffix}{image_ext}",
                    f"{root}/{img_folder}/{image_file}{folder_suffix}{image_ext}",
                    fmt_out="GTIFF",
                    max_shift=max_shift,
                )

                CR.calculate_spatial_shifts()
                CR.correct_shifts()

                print(f"{image_file}{folder_suffix}{image_ext} coregistered")
                total_coregistered += 1
            except Exception:
                print(f"{image_file}{folder_suffix}{image_ext} failed to coregister")

                shutil.copy(
                    f"{backup}/{img_folder}/{image_file}{folder_suffix}{image_ext}",
                    f"{root}/{img_folder}/{image_file}{folder_suffix}{image_ext}",
                )

        shutil.copy(
            f"{backup}/{meta_folder}/{image_file}{meta_ext}",
            f"{root}/{meta_folder}/{image_file}{meta_ext}",
        )

    for img_folder in img_folders:
        if satellite == "L7" or satellite == "L8" or satellite == "S2":
            folder_suffix = f"_{img_folder}"
        else:
            folder_suffix = ""

        shutil.copy(
            f"{backup}/{img_folder}/{reference_file}{folder_suffix}{image_ext}",
            f"{root}/{img_folder}/{reference_file}{folder_suffix}{image_ext}",
        )
    shutil.copy(
        f"{backup}/{meta_folder}/{reference_file}{meta_ext}",
        f"{root}/{meta_folder}/{reference_file}{meta_ext}",
    )

    print("------------------------------------------------")
    print(
        "Total images {}:                    {}".format(
            satellite, (len(img_folders) * len(image_files) + 1)
        )
    )
    print(
        "Images coregistered {}:             {}".format(
            satellite, total_coregistered + 1
        )
    )
    print("------------------------------------------------")

    if remove_backup:
        shutil.rmtree(backup)
