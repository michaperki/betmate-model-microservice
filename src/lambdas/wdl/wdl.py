from typing import Dict, Optional, Tuple
from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load, ndarray
from math import pow
import json
from os import environ
from sys import platform
import atexit
import os
import time
import random
from functools import lru_cache
from logger import log_event

# Config
TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.2))  # Increased from 0.01 to give engine enough time
HASH_SIZE = int(environ.get('HASH_SIZE', 128))  # Reduced from 256 to lower memory usage
CACHE_EXPIRY_TIME = int(environ.get('CACHE_EXPIRY_TIME', 300))  # Cache expiry in seconds (5 min default)

# Engine provider selection: 'stockfish' | 'lc0'
ENGINE_PROVIDER = environ.get('ENGINE_PROVIDER', 'stockfish').lower()

# Optional LC0 configuration (only used if ENGINE_PROVIDER=lc0)
LILA_ENGINE_PATH = environ.get('LILA_ENGINE_PATH')  # e.g., '/var/task/assets/lc0'
LILA_WEIGHTS_PATH = environ.get('LILA_WEIGHTS_PATH')  # e.g., '/var/task/assets/weights.pb.gz'
LILA_BACKEND = environ.get('LILA_BACKEND')  # e.g., 'blas', 'cuda', 'cuda-fp16'
LILA_DEPTH = environ.get('LILA_DEPTH')  # optional depth; if unset, uses TIME_LIMIT

# Blend controls (engine WDL vs time-table). Only applies if engine WDL available.
ENABLE_ENGINE_WDL_BLEND = environ.get('ENABLE_ENGINE_WDL_BLEND', 'true').lower() in ('1','true','yes','on')
ENGINE_WDL_BASE_WEIGHT = float(environ.get('ENGINE_WDL_BASE_WEIGHT', '0.6'))  # baseline engine weight
ENGINE_WDL_MAX_WEIGHT = float(environ.get('ENGINE_WDL_MAX_WEIGHT', '0.9'))  # cap on engine weight

# Global engine instance (Singleton pattern)
_ENGINE: Optional[SimpleEngine] = None

# Result cache to avoid redundant WDL computations
_CACHE = {}

def get_engine():
    """Return or create a Stockfish engine instance (singleton pattern)."""
    global _ENGINE

    if _ENGINE is None:
        log_event('debug', 'stockfish_init_start')
        STOCKFISH_PATH = environ.get('STOCKFISH_PATH', None)
        if STOCKFISH_PATH and os.path.exists(STOCKFISH_PATH):
            log_event('debug', 'stockfish_init_configured', path=STOCKFISH_PATH)
            _ENGINE = SimpleEngine.popen_uci(STOCKFISH_PATH)
        else:
            try:
                executable = f'stockfish_{"mac" if platform == "darwin" else "linux"}'
                bundled_path = f'./assets/{executable}'
                log_event('debug', 'stockfish_init_bundled', path=bundled_path)
                _ENGINE = SimpleEngine.popen_uci(bundled_path)
            except Exception as e:
                fallback_path = os.path.join(os.getcwd(), "assets", executable)
                log_event('debug', 'stockfish_init_fallback', path=fallback_path)
                _ENGINE = SimpleEngine.popen_uci(fallback_path)

        _ENGINE.configure({"Hash": HASH_SIZE})
        log_event('info', 'stockfish_init_success', hash_size=HASH_SIZE)
        print(f"Successfully initialized Stockfish from {STOCKFISH_PATH or bundled_path}")

        # Register cleanup handler
        atexit.register(cleanup_engine)

    # Engine is already cached, no need to log anything
    return _ENGINE


def cleanup_engine():
    """Clean up the engine when the application exits."""
    global _ENGINE
    if _ENGINE:
        print("Shutting down Stockfish engine...")
        _ENGINE.quit()
        _ENGINE = None


# Load model data at module level for Lambda cold start
try:
    with open('./assets/black_win_fraction.npy', 'rb') as f:
        bwf: ndarray = load(f)
    with open('./assets/white_win_fraction.npy', 'rb') as f:
        wwf: ndarray = load(f)
    with open('./assets/draw_fraction.npy', 'rb') as f:
        df: ndarray = load(f)
    log_event('info', 'model_data_loaded')
except Exception as e:
    log_event('error', 'model_data_load_failed', error=str(e))
    # Create dummy model data for fallback
    import numpy as np
    log_event('warning', 'using_fallback_model_data')
    shape = (181, 181, 5)  # Max time 180 seconds + 1 for indexing, 5 bins
    bwf = np.full(shape, 0.33)
    wwf = np.full(shape, 0.33)
    df = np.full(shape, 0.34)


def clean_cache():
    """Remove expired items from the cache."""
    global _CACHE
    current_time = time.time()

    # Create a list of keys to remove to avoid modifying dict during iteration
    keys_to_remove = []
    for key, (timestamp, _) in _CACHE.items():
        if current_time - timestamp > CACHE_EXPIRY_TIME:
            keys_to_remove.append(key)

    # Remove expired items
    for key in keys_to_remove:
        del _CACHE[key]

    if keys_to_remove:
        log_event('debug', 'cache_cleaned', removed_items=len(keys_to_remove), cache_size=len(_CACHE))


# Using functools.lru_cache for the CPU-intensive part of the computation
@lru_cache(maxsize=128)
def _compute_win_bin_cached(fen: str) -> int:
    """
    Core computation logic for win_bin, cached by FEN string.
    This function is separated to enable effective caching.
    """
    board = Board(fen)
    # If LC0 is enabled, derive bin from LC0 p(win)
    if ENGINE_PROVIDER == 'lc0' and LILA_ENGINE_PATH:
        try:
            pwin, _ = _lc0_analyse(board)
        except Exception:
            pwin = None
        if pwin is not None:
            if pwin < 0.10:
                return 0
            elif pwin < 0.40:
                return 1
            elif pwin < 0.60:
                return 2
            elif pwin < 0.90:
                return 3
            else:
                return 4
    engine = get_engine()

    try:
        # Evaluate board with enough time for reliable analysis
        try:
            import asyncio
            try:
                info = engine.analyse(board, Limit(time=TIME_LIMIT))
                score = info['score'].white().score(mate_score=1000)
                # No debug log here to reduce noise - will log in the wrapper function
            except asyncio.exceptions.TimeoutError as te:
                log_event('warning', 'stockfish_timeout', error=str(te), fen=fen)
                # Use neutral evaluation on timeout
                score = 0
            except Exception as e:
                log_event('warning', 'stockfish_analysis_failed', error=str(e), fen=fen)
                # Default to neutral evaluation if analysis fails
                score = 0
        except Exception as outer_e:
            log_event('error', 'stockfish_outer_exception', error=str(outer_e), fen=fen)
            score = 0
    except Exception as e:
        log_event('error', 'engine_handling_error', error=str(e), fen=fen)
        score = 0

    # Logistic transform on evaluation
    pwin = 1 / (1 + pow(10, -score / 400))

    if pwin < 0.10:
        return 0
    elif pwin >= 0.10 and pwin < 0.40:
        return 1
    elif pwin >= 0.40 and pwin < 0.60:
        return 2
    elif pwin >= 0.60 and pwin < 0.90:
        return 3
    else:  # pwin >= 0.90
        return 4


def get_win_bin(board: Board, engine=None) -> int:
    """
    Convert `board` state to 'bin' corresponding to 'white vs. black' favorability.
    Uses the provided engine instance or creates a temporary one if None.

    This function implements a two-level caching strategy:
    1. First checks the in-memory dict cache with timestamps for recently computed positions
    2. Then uses the LRU cache for frequently computed positions (even if not recent)
    """
    # Clean expired entries occasionally (1% chance each call, to avoid overhead)
    if random.random() < 0.01:
        clean_cache()

    # Convert board to FEN for cache key
    fen = board.fen()
    current_time = time.time()

    # Check if we have a cached result
    if fen in _CACHE:
        timestamp, win_bin = _CACHE[fen]
        # Only use cache if not expired
        if current_time - timestamp <= CACHE_EXPIRY_TIME:
            log_event('debug', 'win_bin_cache_hit', fen=fen)
            return win_bin

    # Not in recent cache, try LRU cache or compute new value
    win_bin = _compute_win_bin_cached(fen)

    # Store in timestamp cache
    _CACHE[fen] = (current_time, win_bin)

    # Only log for new computations, but sample to reduce noise
    if random.random() < 0.1:  # Only log 10% of calculations to reduce volume
        log_event('debug', 'win_probability_calculated', pwin_bin=win_bin, fen=fen)

    return win_bin


def get_result_key(fen: str, white_time: int, black_time: int) -> str:
    """Create a cache key for the results cache."""
    return f"{fen}|{white_time}|{black_time}"


# Cache for the final WDL results
_RESULT_CACHE = {}


def _normalize_probs(w: float, d: float, b: float) -> Tuple[float, float, float]:
    s = max(1e-12, float(w) + float(d) + float(b))
    return float(w) / s, float(d) / s, float(b) / s


def _blend_with_engine_wdl(table: Dict[str, float], engine_wdl: Dict[str, float], pwin: float,
                           white_time: int, black_time: int, fen: str) -> Dict[str, float]:
    try:
        ew, ed, eb = _normalize_probs(engine_wdl.get('white_win', 0.0), engine_wdl.get('draw', 0.0), engine_wdl.get('black_win', 0.0))
        tw, td, tb = _normalize_probs(table.get('white_win', 0.0), table.get('draw', 0.0), table.get('black_win', 0.0))

        closeness = max(0.0, 1.0 - 2.0 * abs(float(pwin) - 0.5))  # [0,1]
        time_factor = max(0.0, min(1.0, (white_time + black_time) / 360.0))

        base = max(0.0, min(1.0, ENGINE_WDL_BASE_WEIGHT))
        cap = max(0.0, min(1.0, ENGINE_WDL_MAX_WEIGHT))
        engine_weight = min(cap, base * (0.5 + 0.5 * closeness) * time_factor)
        table_weight = 1.0 - engine_weight

        bw = engine_weight * ew + table_weight * tw
        bd = engine_weight * ed + table_weight * td
        bb = engine_weight * eb + table_weight * tb
        bw, bd, bb = _normalize_probs(bw, bd, bb)
        if random.random() < 0.05:
            log_event('debug', 'lc0_blend', fen=fen, engine_weight=engine_weight,
                      engine_wdl={'w': ew, 'd': ed, 'b': eb},
                      table={'w': tw, 'd': td, 'b': tb}, blended={'w': bw, 'd': bd, 'b': bb})
        return {'white_win': bw, 'draw': bd, 'black_win': bb}
    except Exception as e:
        if random.random() < 0.01:
            log_event('warning', 'lc0_blend_failed', error=str(e))
        return table


def _lc0_analyse(board: Board) -> Tuple[Optional[float], Optional[Dict[str, float]]]:
    """Run a short lc0 analysis and return (pwin_white, wdl_probs_white_pov) or (None, None).

    Uses env: LILA_ENGINE_PATH, LILA_WEIGHTS_PATH, LILA_BACKEND, LILA_DEPTH, TIME_LIMIT
    """
    try:
        import subprocess, re
    except Exception:
        return None, None

    if not LILA_ENGINE_PATH or not os.path.exists(LILA_ENGINE_PATH):
        return None, None

    cmd = [LILA_ENGINE_PATH]
    if LILA_WEIGHTS_PATH:
        cmd.append(f"--weights={LILA_WEIGHTS_PATH}")
    if LILA_BACKEND:
        cmd.append(f"--backend={LILA_BACKEND}")
    cmd.extend(["--show-wdl", "--preload"])  # faster init + explicit WDL

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
        )
    except Exception:
        return None, None

    def send(s: str):
        try:
            proc.stdin.write(s + "\n")
            proc.stdin.flush()
        except Exception:
            pass

    # Handshake
    import time as _t
    send("uci")
    t0 = _t.time()
    while True:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None or _t.time() - t0 > 10:
                proc.kill()
                return None, None
            continue
        if "uciok" in line:
            break
        if _t.time() - t0 > 10:
            proc.kill()
            return None, None

    # Enable WDL and ready
    send("setoption name UCI_ShowWDL value true")
    send("isready")
    t0 = _t.time()
    while True:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None or _t.time() - t0 > 10:
                proc.kill()
                return None, None
            continue
        if "readyok" in line:
            break
        if _t.time() - t0 > 10:
            proc.kill()
            return None, None

    # Position + go
    send(f"position fen {board.fen()}")
    if LILA_DEPTH:
        try:
            d = int(LILA_DEPTH)
            send(f"go depth {d}")
        except Exception:
            ms = int(max(10, TIME_LIMIT * 1000))
            send(f"go movetime {ms}")
    else:
        ms = int(max(10, TIME_LIMIT * 1000))
        send(f"go movetime {ms}")

    # Parse wdl
    wdl_re = re.compile(r"(?i)wdl\s*[:=]?\s*([0-9]+)[ ,/]+([0-9]+)[ ,/]+([0-9]+)")
    wins = draws = losses = None
    t0 = _t.time()
    while True:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None or _t.time() - t0 > 30:
                break
            continue
        m = wdl_re.search(line)
        if m:
            try:
                wins = int(m.group(1)); draws = int(m.group(2)); losses = int(m.group(3))
            except Exception:
                pass
        if line.startswith("bestmove"):
            break
        if _t.time() - t0 > 30:
            break

    try:
        send("quit")
        proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    if not all(isinstance(x, int) for x in (wins, draws, losses)):
        return None, None
    s = wins + draws + losses
    if s <= 0:
        return None, None

    sm_w, sm_d, sm_l = wins / s, draws / s, losses / s  # side-to-move POV
    # Convert to White POV
    if board.turn:  # White to move
        w_w, w_d, w_l = sm_w, sm_d, sm_l
    else:
        w_w, w_d, w_l = sm_l, sm_d, sm_w
    pwin = max(0.0, min(1.0, float(w_w)))
    return pwin, {'white_win': w_w, 'draw': w_d, 'black_win': w_l}


def model(board: Board, white_time: int, black_time: int, game_id: str = None, move_number: int = None) -> Dict[str, float]:
    """
    Get win/draw/loss probabilities based on `board` state and player times.

    Args:
        board: Chess board position
        white_time: White player's remaining time in seconds
        black_time: Black player's remaining time in seconds
        game_id: Optional game ID for logging correlation
        move_number: Optional move number for logging correlation

    Returns:
        Dictionary with white_win, draw, and black_win probabilities
    """
    fen = board.fen()
    is_whites_turn = " w " in fen
    player_color = "white" if is_whites_turn else "black"

    # Create and log correlation ID for this calculation
    log_context = {
        'fen': fen,
        'white_time': white_time,
        'black_time': black_time,
        'player_to_move': player_color
    }

    # Add optional game tracking info if provided
    if game_id:
        log_context['game_id'] = game_id
    if move_number is not None:
        log_context['move_number'] = move_number

    # Check results cache first
    cache_key = get_result_key(fen, white_time, black_time)
    current_time = time.time()

    if cache_key in _RESULT_CACHE:
        timestamp, result = _RESULT_CACHE[cache_key]
        if current_time - timestamp <= CACHE_EXPIRY_TIME:
            # Sample cache hit logs to reduce noise
            if random.random() < 0.05:  # Only log 5% of cache hits
                log_event('debug', 'model_calculation_cache_hit', **log_context)
            return result

    # Use 'debug' for start but sample to reduce log volume
    if random.random() < 0.2:  # Log 20% of calculation starts
        log_event('debug', 'model_calculation_start', **log_context)

    # Ensure times are within range of model
    white_time_adjusted = min(180, max(1, white_time))
    black_time_adjusted = min(180, max(1, black_time))

    if white_time_adjusted != white_time or black_time_adjusted != black_time:
        log_event('debug', 'time_adjusted',
                 original_white=white_time,
                 adjusted_white=white_time_adjusted,
                 original_black=black_time,
                 adjusted_black=black_time_adjusted)

    # Use a single engine instance for the entire model calculation
    try:
        win_bin: int = get_win_bin(board, get_engine())
    except Exception as e:
        log_event('error', 'engine_analysis_error', error=str(e), **log_context)
        # Default to balanced position (bin 2) if everything fails
        win_bin = 2

    # Calculate base result from lookup table using adjusted times
    table = {
        'white_win': float(wwf[white_time_adjusted, black_time_adjusted, win_bin]),
        'draw': float(df[white_time_adjusted, black_time_adjusted, win_bin]),
        'black_win': float(bwf[white_time_adjusted, black_time_adjusted, win_bin])
    }

    # If LC0 is enabled, blend LC0 WDL with table odds
    result = table
    if ENGINE_PROVIDER == 'lc0' and LILA_ENGINE_PATH and ENABLE_ENGINE_WDL_BLEND:
        try:
            pwin, wdl = _lc0_analyse(board)
        except Exception as e:
            pwin, wdl = None, None
        if pwin is not None and isinstance(wdl, dict):
            result = _blend_with_engine_wdl(table, wdl, pwin, white_time_adjusted, black_time_adjusted, board.fen())

    # Store in cache
    _RESULT_CACHE[cache_key] = (current_time, result)

    # Create a summary log with all relevant information in one place
    log_event('info', 'move_analysis_complete',
             win_bin=win_bin,
             probabilities=result,
             **log_context)

    return result


def wdl_route(event, context=None):
    """
    Handler of AWS Lambda call.
    Parses input and passes it to `model()`.

    Will return 400 if:
    - `fen` is not provided or not in proper notation
    - `white_time` is not provided or can't be cast to int
    - `black_time` is not provided or can't be cast to int

    Optional parameters:
    - `game_id`: ID of the game for correlation in logs
    - `move_number`: Current move number for correlation in logs

    Otherwise, will return result from `model()` with 200 status.
    """
    # Get trace ID from request if available
    trace_id = None
    if event.get('headers'):
        trace_id = event['headers'].get('x-trace-id')

    # Log with trace ID if available
    log_context = {}
    if trace_id:
        log_context['trace_id'] = trace_id

    log_event('debug', 'wdl_request_received', **log_context)

    data = event['queryStringParameters']
    try:
        # Extract game_id and move_number if provided
        game_id = data.get('game_id')
        move_number = None
        if 'move_number' in data:
            try:
                move_number = int(data.get('move_number'))
            except (ValueError, TypeError):
                log_event('warning', 'invalid_move_number_ignored', **log_context)

        if game_id:
            log_context['game_id'] = game_id
        if move_number is not None:
            log_context['move_number'] = move_number

        # Handle empty FEN (this was causing issues)
        fen = data.get('fen')
        if fen is None or fen.strip() == "":
            # Default to starting position if FEN is empty
            log_event('warning', 'empty_fen_using_default', **log_context)
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        board = Board(fen)
        log_context['fen'] = fen

        # Record current player from FEN
        player_color = "white" if " w " in fen else "black"
        log_context['player_to_move'] = player_color

        # Handle missing time parameters
        try:
            white_time: int = int(data.get('white_time', 60))
            log_context['white_time'] = white_time
        except (ValueError, TypeError):
            log_event('warning', 'invalid_white_time_using_default', **log_context)
            white_time = 60
            log_context['white_time'] = white_time

        try:
            black_time: int = int(data.get('black_time', 60))
            log_context['black_time'] = black_time
        except (ValueError, TypeError):
            log_event('warning', 'invalid_black_time_using_default', **log_context)
            black_time = 60
            log_context['black_time'] = black_time

    except Exception as e:
        log_event('error', 'request_parsing_error', error=str(e), **log_context)
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }

    try:
        # Pass game_id and move_number to model for correlation
        probabilities = model(board, white_time, black_time, game_id, move_number)

        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": "SUCCESS",
                "data": probabilities,
                "meta": {
                    "game_id": game_id,
                    "move_number": move_number,
                    "player_to_move": player_color
                } if game_id or move_number else None
            })
        }
    except Exception as e:
        log_event('error', 'model_calculation_failed', error=str(e), **log_context)
        # Return default probabilities if model fails
        return {
            'statusCode': 200,  # Return 200 to avoid client errors
            'body': json.dumps({
                "message": "WARNING: Used fallback values due to analysis error",
                "data": {
                    "white_win": 0.33,
                    "draw": 0.34,
                    "black_win": 0.33
                },
                "meta": {
                    "game_id": game_id,
                    "move_number": move_number,
                    "player_to_move": player_color,
                    "error": str(e)
                } if game_id or move_number else {"error": str(e)}
            })
        }


def handler(event, context):
    """AWS Lambda handler function"""
    return wdl_route(event, context)


# --- Local‑dev server (optional) ---------------------------
if __name__ == "__main__" and environ.get("LOCAL_DEV") == "true":
    from flask import Flask, request
    import threading

    lock = threading.Lock()
    app = Flask(__name__)

    @app.route("/predict", methods=["POST"])
    def predict_route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        with lock:
            return wdl_route({"queryStringParameters": data})

    # Warm the engine for faster local calls
    get_engine()
    log_event('info', 'local_dev_server_starting', port=8080)
    app.run(host="0.0.0.0", port=8080, threaded=False)
