from datasets import Dataset


def main():
    dataset = Dataset.from_dict({"id": [10, 20, 30]})
    selected = dataset.select([2, 0])

    assert dataset[0] == {"id": 10}, dataset[0]
    assert list(dataset[:]["id"]) == [10, 20, 30], dataset[:]
    assert selected[0] == {"id": 30}, selected[0]
    assert selected[-1] == {"id": 10}, selected[-1]
    assert list(selected[:]["id"]) == [30, 10], selected[:]
    assert list(selected[[1, 0]]["id"]) == [10, 30], selected[[1, 0]]
    assert selected.with_format("numpy")[:]["id"].tolist() == [30, 10]


if __name__ == "__main__":
    main()
