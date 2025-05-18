#!/usr/bin/env python3
"""
Simple test script to verify the memory usage of our singleton engine pattern.
This will run multiple analyses and monitor memory usage.
"""
import chess
import time
from move_analysis import get_engine, get_all_move_ratings, cleanup_engine
import os
import psutil

# Get initial memory usage
process = psutil.Process(os.getpid())
initial_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB

print(f"Initial memory usage: {initial_memory:.2f} MB")

# Initialize the engine (should happen only once)
start_time = time.time()
engine = get_engine()
print(f"Engine initialization time: {time.time() - start_time:.2f} seconds")

# Check memory after initialization
after_init_memory = process.memory_info().rss / 1024 / 1024
print(f"Memory after engine init: {after_init_memory:.2f} MB (delta: {after_init_memory - initial_memory:.2f} MB)")

# Test positions (mid-game positions with decent complexity)
fen_positions = [
    "r1bqkb1r/ppp2ppp/2np1n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5",  # Italian Game
    "rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5",  # Queen's Gambit
    "r1bq1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1BP2/PPPQ2PP/R3K2R w KQ - 3 9",     # King's Indian
    "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 0 7", # Neo-Grünfeld
]

# Run analyses on each position
for i, fen in enumerate(fen_positions):
    print(f"\nAnalyzing position {i+1}/{len(fen_positions)}...")
    board = chess.Board(fen)
    
    start_time = time.time()
    all_moves = get_all_move_ratings(board)
    
    # Print top 3 moves
    sorted_moves = sorted(all_moves.items(), key=lambda x: -x[1]["score"])
    print(f"Top 3 moves:")
    for j in range(min(3, len(sorted_moves))):
        move, data = sorted_moves[j]
        print(f"  {j+1}. {move} (score: {data['score']}, percentile: {data['percentile']})")
    
    print(f"Analysis time: {time.time() - start_time:.2f} seconds")
    
    # Check memory after this analysis
    current_memory = process.memory_info().rss / 1024 / 1024
    print(f"Current memory usage: {current_memory:.2f} MB (delta: {current_memory - initial_memory:.2f} MB)")
    time.sleep(1)  # Small pause between analyses

# Cleanup
cleanup_engine()
print("\nEngine cleaned up.")

# Final memory check
final_memory = process.memory_info().rss / 1024 / 1024
print(f"Final memory usage: {final_memory:.2f} MB")
print(f"Memory change after cleanup: {final_memory - current_memory:.2f} MB")
print(f"Total memory change: {final_memory - initial_memory:.2f} MB")

print("\nTest completed successfully!")