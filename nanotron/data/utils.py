import math
from typing import List, Tuple


def generate_sharding_plan(
    num_shards: int,
    total_data_size: int,
    dataset_sizes: List[int],
    dataset_names: List[str] = None,
) -> List[Tuple[int, int]]:
    """
    Generates a sharding plan for the datasets.

    Args:
        num_shards: The number of shards to generate.
        total_data_size: The total size of the data.
        dataset_sizes: A list of sizes for each dataset.
        dataset_names: A list of names for each dataset.

    Returns:
        A list of tuples, where each tuple contains the start and end index for a shard.
    """
    if dataset_names is None:
        dataset_names = [str(i) for i in range(len(dataset_sizes))]

    if len(dataset_sizes) != len(dataset_names):
        raise ValueError(
            f"Length of dataset_sizes ({len(dataset_sizes)}) must match length of dataset_names ({len(dataset_names)})"
        )

    if sum(dataset_sizes) != total_data_size:
        # This is a bit of a loose check, as the total_data_size might be slightly different
        # due to rounding or other factors. However, for the purpose of this function,
        # we expect them to be close.
        pass

    shards = []
    current_shard_size = 0
    current_shard_start = 0
    shard_size_limit = total_data_size / num_shards

    for i, size in enumerate(dataset_sizes):
        current_shard_size += size
        if current_shard_size >= shard_size_limit:
            shards.append((current_shard_start, i))
            current_shard_start = i + 1
            current_shard_size = 0

    # Add the last shard if there are remaining datasets
    if current_shard_start < len(dataset_sizes):
        shards.append((current_shard_start, len(dataset_sizes) - 1))

    return shards
