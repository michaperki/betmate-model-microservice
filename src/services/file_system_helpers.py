from sys import platform
import os


def get_asset_path(f: str):
    return os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, f'assets/{f}')


def get_stockfish_executable_path():
    executable = f"stockfish_{'mac' if platform == 'darwin' else 'linux'}"
    return get_asset_path(executable)
