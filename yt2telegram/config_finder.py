from glob import glob
from pathlib import Path

def find_channel_configs(path="yt2telegram/channels/*.yml"):
    # Get all matching files
    all_configs = glob(path, recursive=True)
    
    # Filter out example/demo configuration files
    example_files = {'example_channel.yml', 'example_multi_model.yml'}
    filtered_configs = [
        config for config in all_configs 
        if Path(config).name not in example_files
    ]
    
    return filtered_configs