from glob import glob
from pathlib import Path

def find_channel_configs(path="yt2telegram/channels/*.yml"):
    # Get all matching files
    all_configs = glob(path, recursive=True)
    
    # Filter out the example_channel.yml
    filtered_configs = [
        config for config in all_configs 
        if Path(config).name != 'example_channel.yml'
    ]
    
    return filtered_configs