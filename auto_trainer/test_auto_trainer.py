from typing import Tuple
import mlrun
import pandas as pd
import pytest
from mlrun import import_function


from sklearn.datasets import (
    make_classification,
    make_multilabel_classification,
    make_regression,
)


MODELS = [
    ("sklearn.linear_model.LinearRegression", "regression"),
    ("sklearn.ensemble.RandomForestClassifier", "classification"),
    ("xgboost.XGBRegressor", "regression"),
    ("lightgbm.LGBMClassifier", "classification"),
]


def _get_dataset(problem_type: str, filepath: str = ".", n_classes: int = 2):
    if problem_type == "classification":
        x, y = make_classification(n_classes=n_classes)
    elif problem_type == "regression":
        x, y = make_regression(n_targets=1)
    elif problem_type == "multilabel_classification":
        x, y = make_multilabel_classification(n_classes=n_classes)
    else:
        raise ValueError(f"Not supporting problem type = {problem_type}")

    features = [f"f_{i}" for i in range(x.shape[1])]
    if y.ndim == 1:
        labels = ["labels"]
    else:
        labels = [f"label_{i}" for i in range(y.shape[1])]
    dataset = pd.concat(
        [pd.DataFrame(x, columns=features), pd.DataFrame(y, columns=labels)], axis=1
    )
    filename = f"{filepath}/{problem_type}_dataset.csv"
    dataset.to_csv(filename, index=False)
    return filename, labels


def _set_environment():
    mlrun.set_env_from_file("mlrun.env")
    mlrun.get_or_create_project("auto-trainer-test", context="./", user_project=True)


@pytest.mark.parametrize("model", MODELS)
def test_train(model: Tuple[str, str]):
    _set_environment()

    dataset, label_columns = _get_dataset(model[1])

    # Importing function:
    fn = import_function("function.yaml")

    train_run = None
    model_name = model[0].split(".")[-1]
    try:
        train_run = fn.run(
            inputs={"dataset": dataset},
            params={
                "drop_columns": ["f_0", "f_2"],
                "model_class": model[0],
                "model_name": f"model_{model_name}",
                "label_columns": label_columns,
                "train_test_split_size": 0.2,
            },
            handler="train",
            local=True,
        )
    except Exception as exception:
        print(f"- The test failed - raised the following error:\n- {exception}")
    assert train_run and all(
        key in train_run.outputs for key in ["model", "test_set"]
    ), "outputs should include more data"


@pytest.mark.parametrize("model", MODELS)
def test_train_evaluate(model: Tuple[str, str]):
    _set_environment()

    dataset, label_columns = _get_dataset(model[1])

    # Importing function:
    fn = import_function("function.yaml")

    evaluate_run = None
    model_name = model[0].split(".")[-1]
    try:
        train_run = fn.run(
            inputs={"dataset": dataset},
            params={
                "drop_columns": ["f_0", "f_2"],
                "model_class": model[0],
                "model_name": f"model_{model_name}",
                "label_columns": label_columns,
                "train_test_split_size": 0.2,
            },
            handler="train",
            local=True,
        )

        evaluate_run = fn.run(
            inputs={"dataset": train_run.outputs["test_set"]},
            params={
                "model": train_run.outputs["model"],
                "drop_columns": ["f_0", "f_2"],
                "label_columns": label_columns,
            },
            handler="evaluate",
            local=True,
        )
    except Exception as exception:
        print(f"- The test failed - raised the following error:\n- {exception}")
    assert (
        evaluate_run and "evaluation-test_set" in evaluate_run.outputs
    ), "Missing fields in evaluate_run"


@pytest.mark.parametrize("model", MODELS)
def test_train_predict(model: Tuple[str, str]):
    _set_environment()

    dataset, label_columns = _get_dataset(model[1])

    # Importing function:
    fn = import_function("function.yaml")

    predict_run = None
    model_name = model[0].split(".")[-1]
    try:
        train_run = fn.run(
            inputs={"dataset": dataset},
            params={
                "drop_columns": ["f_0", "f_2"],
                "model_class": model[0],
                "model_name": f"model_{model_name}",
                "label_columns": label_columns,
                "train_test_split_size": 0.2,
            },
            handler="train",
            local=True,
        )

        predict_run = fn.run(
            inputs={"dataset": train_run.outputs["test_set"]},
            params={
                "model": train_run.outputs["model"],
                "drop_columns": ["f_0", "f_2"],
                "label_columns": label_columns,
            },
            handler="predict",
            local=True,
        )
    except Exception as exception:
        print(f"- The test failed - raised the following error:\n- {exception}")
    assert (
        predict_run and "prediction" in predict_run.outputs
    ), "Prediction field must be in the output"
