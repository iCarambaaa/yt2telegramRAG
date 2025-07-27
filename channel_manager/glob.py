import glob
from pathlib import Path

def find_channel_configs(path="channel_manager/channels/*.yml"):
    # Get all matching files
    all_configs = glob.glob(path, recursive=True)
    
    # Filter out the example_channel.yml
    filtered_configs = [
        config for config in all_configs 
        if Path(config).name != 'example_channel.yml'
    ]
    
    return filtered_configs