#
# Copyright (c) 2020, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import glob
import math

import cudf
import numpy as np
import pytest
from cudf.tests.utils import assert_eq

import nvtabular as nvt
import nvtabular.io
import nvtabular.ops as ops
from tests.conftest import allcols_csv, cleanup, mycols_csv, mycols_pq


@cleanup
@pytest.mark.parametrize("gpu_memory_frac", [0.01, 0.1])
@pytest.mark.parametrize("engine", ["parquet", "csv", "csv-no-header"])
@pytest.mark.parametrize("op_columns", [["x"], None])
def test_minmax(tmpdir, datasets, gpu_memory_frac, engine, op_columns):
    paths = glob.glob(str(datasets[engine]) + "/*." + engine.split("-")[0])

    if engine == "parquet":
        df1 = cudf.read_parquet(paths[0])[mycols_pq]
        df2 = cudf.read_parquet(paths[1])[mycols_pq]
    else:
        df1 = cudf.read_csv(paths[0], header=False, names=allcols_csv)[mycols_csv]
        df2 = cudf.read_csv(paths[1], header=False, names=allcols_csv)[mycols_csv]
    df = cudf.concat([df1, df2], axis=0)
    df["id"] = df["id"].astype("int64")

    if engine == "parquet":
        cat_names = ["name-cat", "name-string"]
        columns = mycols_pq
    else:
        cat_names = ["name-string"]
        columns = mycols_csv
    cont_names = ["x", "y", "id"]
    label_name = ["label"]

    data_itr = nvtabular.io.GPUDatasetIterator(
        paths,
        columns=columns,
        use_row_groups=True,
        gpu_memory_frac=gpu_memory_frac,
        names=allcols_csv,
    )

    config = nvtabular.workflow.get_new_config()
    config["PP"]["all"] = [ops.MinMax(columns=op_columns)]

    processor = nvtabular.Workflow(
        cat_names=cat_names,
        cont_names=cont_names,
        label_name=label_name,
        config=config,
        to_cpu=False,
    )

    processor.update_stats(data_itr)

    x_min = df["x"].min()

    assert x_min == pytest.approx(processor.stats["mins"]["x"], 1e-2)
    x_max = df["x"].max()
    assert x_max == pytest.approx(processor.stats["maxs"]["x"], 1e-2)
    if not op_columns:
        name_min = min(df["name-string"].tolist())
        name_max = max(df["name-string"].tolist())
        assert name_min == processor.stats["mins"]["name-string"]
        y_max = df["y"].max()
        y_min = df["y"].min()
        assert y_max == processor.stats["maxs"]["y"]
        assert name_max == processor.stats["maxs"]["name-string"]
        assert y_min == processor.stats["mins"]["y"]
    return processor.ds_exports


@cleanup
@pytest.mark.parametrize("gpu_memory_frac", [0.01, 0.1])
@pytest.mark.parametrize("engine", ["parquet", "csv", "csv-no-header"])
@pytest.mark.parametrize("op_columns", [["x"], None])
def test_moments(tmpdir, datasets, gpu_memory_frac, engine, op_columns):
    paths = glob.glob(str(datasets[engine]) + "/*." + engine.split("-")[0])

    if engine == "parquet":
        df1 = cudf.read_parquet(paths[0])[mycols_pq]
        df2 = cudf.read_parquet(paths[1])[mycols_pq]
    else:
        df1 = cudf.read_csv(paths[0], header=False, names=allcols_csv)[mycols_csv]
        df2 = cudf.read_csv(paths[1], header=False, names=allcols_csv)[mycols_csv]
    df = cudf.concat([df1, df2], axis=0)
    df["id"] = df["id"].astype("int64")

    if engine == "parquet":
        cat_names = ["name-cat", "name-string"]
        columns = mycols_pq
    else:
        cat_names = ["name-string"]
        columns = mycols_csv
    cont_names = ["x", "y", "id"]
    label_name = ["label"]

    data_itr = nvtabular.io.GPUDatasetIterator(
        paths,
        columns=columns,
        use_row_groups=True,
        gpu_memory_frac=gpu_memory_frac,
        names=allcols_csv,
    )

    config = nvt.workflow.get_new_config()
    config["PP"]["continuous"] = [ops.Moments(columns=op_columns)]

    processor = nvt.Workflow(
        cat_names=cat_names,
        cont_names=cont_names,
        label_name=label_name,
        config=config,
        to_cpu=False,
    )

    processor.update_stats(data_itr)

    # Check mean and std
    assert math.isclose(df.x.mean(), processor.stats["means"]["x"], rel_tol=1e-4)
    assert math.isclose(df.x.std(), processor.stats["stds"]["x"], rel_tol=1e-3)
    if not op_columns:
        assert math.isclose(df.y.mean(), processor.stats["means"]["y"], rel_tol=1e-4)
        assert math.isclose(df.id.mean(), processor.stats["means"]["id"], rel_tol=1e-4)

        assert math.isclose(df.y.std(), processor.stats["stds"]["y"], rel_tol=1e-3)
        assert math.isclose(df.id.std(), processor.stats["stds"]["id"], rel_tol=1e-3)
    return processor.ds_exports


@cleanup
@pytest.mark.parametrize("gpu_memory_frac", [0.01, 0.1])
@pytest.mark.parametrize("engine", ["parquet", "csv", "csv-no-header"])
@pytest.mark.parametrize("op_columns", [["name-string"], None])
def test_encoder(tmpdir, datasets, gpu_memory_frac, engine, op_columns):
    paths = glob.glob(str(datasets[engine]) + "/*." + engine.split("-")[0])

    if engine == "parquet":
        df1 = cudf.read_parquet(paths[0])[mycols_pq]
        df2 = cudf.read_parquet(paths[1])[mycols_pq]
    else:
        df1 = cudf.read_csv(paths[0], header=False, names=allcols_csv)[mycols_csv]
        df2 = cudf.read_csv(paths[1], header=False, names=allcols_csv)[mycols_csv]
    df = cudf.concat([df1, df2], axis=0)
    df["id"] = df["id"].astype("int64")

    if engine == "parquet":
        cat_names = ["name-cat", "name-string"]
        columns = mycols_pq
    else:
        cat_names = ["name-string"]
        columns = mycols_csv
    cont_names = ["x", "y", "id"]
    label_name = ["label"]

    data_itr = nvtabular.io.GPUDatasetIterator(
        paths,
        columns=columns,
        use_row_groups=True,
        gpu_memory_frac=gpu_memory_frac,
        names=allcols_csv,
    )

    config = nvt.workflow.get_new_config()
    config["PP"]["categorical"] = [ops.Encoder(columns=op_columns)]

    processor = nvt.Workflow(
        cat_names=cat_names,
        cont_names=cont_names,
        label_name=label_name,
        config=config,
        to_cpu=False,
    )

    processor.update_stats(data_itr)

    # Check that categories match
    if engine == "parquet" and not op_columns:
        cats_expected0 = df["name-cat"].unique().values_to_string()
        cats0 = processor.stats["encoders"]["name-cat"].get_cats().values_to_string()
        assert cats0 == ["None"] + cats_expected0
    cats_expected1 = df["name-string"].unique().values_to_string()
    cats1 = processor.stats["encoders"]["name-string"].get_cats().values_to_string()
    assert cats1 == ["None"] + cats_expected1
    return processor.ds_exports


@cleanup
@pytest.mark.parametrize("gpu_memory_frac", [0.01, 0.1])
@pytest.mark.parametrize("engine", ["parquet", "csv", "csv-no-header"])
@pytest.mark.parametrize("op_columns", [["x"], None])
def test_median(tmpdir, datasets, gpu_memory_frac, engine, op_columns):
    paths = glob.glob(str(datasets[engine]) + "/*." + engine.split("-")[0])

    if engine == "parquet":
        df1 = cudf.read_parquet(paths[0])[mycols_pq]
        df2 = cudf.read_parquet(paths[1])[mycols_pq]
    else:
        df1 = cudf.read_csv(paths[0], header=False, names=allcols_csv)[mycols_csv]
        df2 = cudf.read_csv(paths[1], header=False, names=allcols_csv)[mycols_csv]
    df = cudf.concat([df1, df2], axis=0)
    df["id"] = df["id"].astype("int64")

    if engine == "parquet":
        cat_names = ["name-cat", "name-string"]
        columns = mycols_pq
    else:
        cat_names = ["name-string"]
        columns = mycols_csv
    cont_names = ["x", "y", "id"]
    label_name = ["label"]

    data_itr = nvtabular.io.GPUDatasetIterator(
        paths,
        columns=columns,
        use_row_groups=True,
        gpu_memory_frac=gpu_memory_frac,
        names=allcols_csv,
    )

    config = nvt.workflow.get_new_config()
    config["PP"]["continuous"] = [ops.Median(columns=op_columns)]

    processor = nvt.Workflow(
        cat_names=cat_names,
        cont_names=cont_names,
        label_name=label_name,
        config=config,
        to_cpu=False,
    )

    processor.update_stats(data_itr)

    # Check median (TODO: Improve the accuracy)
    x_median = df.x.dropna().quantile(0.5, interpolation="linear")
    assert math.isclose(x_median, processor.stats["medians"]["x"], rel_tol=1e1)
    if not op_columns:
        y_median = df.y.dropna().quantile(0.5, interpolation="linear")
        id_median = df.id.dropna().quantile(0.5, interpolation="linear")
        assert math.isclose(y_median, processor.stats["medians"]["y"], rel_tol=1e1)
        assert math.isclose(id_median, processor.stats["medians"]["id"], rel_tol=1e1)
    return processor.ds_exports


@pytest.mark.parametrize("gpu_memory_frac", [0.01, 0.1])
@pytest.mark.parametrize("engine", ["parquet", "csv", "csv-no-header"])
@pytest.mark.parametrize("op_columns", [["x"], None])
def test_log(tmpdir, datasets, gpu_memory_frac, engine, op_columns):
    paths = glob.glob(str(datasets[engine]) + "/*." + engine.split("-")[0])

    if engine == "parquet":
        df1 = cudf.read_parquet(paths[0])[mycols_pq]
        df2 = cudf.read_parquet(paths[1])[mycols_pq]
    else:
        df1 = cudf.read_csv(paths[0], header=False, names=allcols_csv)[mycols_csv]
        df2 = cudf.read_csv(paths[1], header=False, names=allcols_csv)[mycols_csv]
    df = cudf.concat([df1, df2], axis=0)
    df["id"] = df["id"].astype("int64")

    if engine == "parquet":
        columns = mycols_pq
    else:
        columns = mycols_csv
    cont_names = ["x", "y", "id"]

    data_itr = nvtabular.io.GPUDatasetIterator(
        paths,
        columns=columns,
        use_row_groups=True,
        gpu_memory_frac=gpu_memory_frac,
        names=allcols_csv,
    )

    log_op = ops.LogOp(columns=op_columns)

    columns_ctx = {}
    columns_ctx["continuous"] = {}
    columns_ctx["continuous"]["base"] = cont_names

    for gdf in data_itr:
        new_gdf = log_op.apply_op(gdf, columns_ctx, "continuous")
        assert new_gdf[cont_names] == np.log(gdf[cont_names].astype(np.float32))


def test_fill_missing(tmpdir, datasets, engine="parquet"):
    paths = glob.glob(str(datasets[engine]) + "/*." + engine.split("-")[0])
    columns = mycols_pq if engine == "parquet" else mycols_csv

    df = cudf.concat([cudf.read_parquet(path) for path in paths])

    data_itr = nvtabular.io.GPUDatasetIterator(
        paths, columns=columns, use_row_groups=True, names=allcols_csv
    )

    op = nvt.ops.FillMissing(42)

    cont_names = ["x", "y"]
    columns_ctx = {}
    columns_ctx["continuous"] = {}
    columns_ctx["continuous"]["base"] = cont_names

    transformed = cudf.concat([op.apply_op(df, columns_ctx, "continuous") for df in data_itr])
    assert_eq(transformed[cont_names], df[cont_names].dropna(42))
