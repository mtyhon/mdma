#!/bin/bash

python3 experiments/BNAF/density_estimation.py --dataset gas --hidden_dim 320 --missing_data_pct "$1" --missing_data_strategy mice --device "cuda:$2"
python3 experiments/BNAF/density_estimation.py --dataset gas --hidden_dim 320 --missing_data_pct "$1" --missing_data_strategy mice --device "cuda:$2"
python3 experiments/BNAF/density_estimation.py --dataset gas --hidden_dim 320 --missing_data_pct "$1" --missing_data_strategy mice --device "cuda:$2"