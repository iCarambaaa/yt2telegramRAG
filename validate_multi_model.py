#!/usr/bin/env python3
"""
Multi-Model Configuration Validation Tool

This script validates your multi-model setup and provides recommendations
for optimal configuration.

Usage:
    python validate_multi_model.py <channel_config_path>
    python validate_multi_model.py yt2telegram/channels/example_multi_model.yml
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from yt2telegram.utils.validators import InputValidator
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

def main():
    console = Console()
    
    if len(sys.argv) != 2:
        console.print("[red]Usage: python validate_multi_model.py <channel_config_path>[/red]")
        console.print("Example: python validate_multi_model.py yt2telegram/channels/example_multi_model.yml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        console.print(f"[red]Configuration file not found: {config_path}[/red]")
        sys.exit(1)
    
    console.print(f"[blue]Validating multi-model configuration: {config_path}[/blue]")
    console.print()
    
    # Run validation
    result = InputValidator.validate_channel_multi_model_setup(config_path)
    
    # Display results
    if result['valid']:
        console.print(Panel("✅ Configuration is valid!", style="green"))
    else:
        console.print(Panel("❌ Configuration has errors!", style="red"))
    
    # Show errors
    if result['errors']:
        console.print("\n[red]Errors:[/red]")
        for error in result['errors']:
            console.print(f"  ❌ {error}")
    
    # Show warnings
    if result['warnings']:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result['warnings']:
            console.print(f"  ⚠️  {warning}")
    
    # Show recommendations
    if result['recommendations']:
        console.print("\n[blue]Recommendations:[/blue]")
        for recommendation in result['recommendations']:
            console.print(f"  💡 {recommendation}")
    
    # Summary
    console.print()
    if result['valid'] and not result['warnings']:
        console.print("[green]🎉 Your multi-model configuration is perfect![/green]")
        console.print("[green]Ready to run: python run.py[/green]")
    elif result['valid']:
        console.print("[yellow]✅ Configuration is valid but has some recommendations.[/yellow]")
        console.print("[yellow]You can proceed with: python run.py[/yellow]")
    else:
        console.print("[red]❌ Please fix the errors before using multi-model summarization.[/red]")
        console.print("[red]See MULTI_MODEL_SETUP.md for detailed configuration help.[/red]")
        sys.exit(1)
    
    # Additional help
    if not result['valid'] or result['warnings'] or result['recommendations']:
        console.print()
        console.print("[blue]📚 For detailed setup help:[/blue]")
        console.print("   • MULTI_MODEL_SETUP.md - Comprehensive configuration guide")
        console.print("   • MULTI_MODEL_QUICKSTART.md - Quick 5-minute setup")
        console.print("   • README.md - General project documentation")

if __name__ == "__main__":
    main()