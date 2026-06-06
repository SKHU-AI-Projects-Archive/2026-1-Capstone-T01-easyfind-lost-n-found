import multiprocessing as mp
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from core.streamer import SourceStreamer
from core.executor import PipelineExecutor
from core.aggregator import OutputAggregator
from core.latest_slot import LatestSlot
from core.utils.config_loader import load_config

def cleanup_abandoned_files(days=10):
    cutoff = datetime.now() - timedelta(days=days)
    abandoned = Path(__file__).parent / 'plugins' / 'abandoned'

    for folder_name in ('scenes', 'logs', 'obj-imgs'):
        base = abandoned / folder_name
        if not base.exists():
            continue
        for pipename_dir in base.iterdir():
            if not pipename_dir.is_dir():
                continue
            for date_dir in pipename_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                try:
                    parts = date_dir.name.split('-')
                    date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    if date < cutoff:
                        shutil.rmtree(date_dir)
                        print(f"[Cleanup] Removed {date_dir}")
                except (ValueError, IndexError):
                    continue


if __name__ == "__main__":
    mp.set_start_method("spawn")
    cleanup_abandoned_files(days=7)
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default="configs/multi_cam.yaml")
    args = parser.parse_args()

    config = load_config(args.config)

    print(f">>> Multi-Source System (Separate Windows) Initialize.")

    result_queue = mp.Queue()
    processes = []
    multi_pipe_queues = {}

    # 1. Pipelines
    for pipe_conf in config.get('pipelines', []):
        if not pipe_conf.get('enable', True): 
            continue
        
        src_id = pipe_conf.get('source_id')
        src_meta = next((s for s in config.get('sources', []) if s['id'] == src_id), None)
        if not src_meta: 
            print(f"Warning: Source ID '{src_id}' not found for pipeline '{pipe_conf.get('name')}'")
            continue
        
        shm_name = src_meta['shared_memory_name']
        p_in_q = LatestSlot()
        if src_id not in multi_pipe_queues: 
            multi_pipe_queues[src_id] = []
        multi_pipe_queues[src_id].append(p_in_q)

        executor = PipelineExecutor(pipe_conf, p_in_q, result_queue, shm_name)
        executor.start()
        processes.append(executor)

    # 2. Aggregator (Separate Windows Mode)
    aggregator = OutputAggregator(config.get('output', {}), result_queue)
    aggregator.start()
    processes.append(aggregator)

    # 3. Streamers
    for src_conf in config.get('sources', []):
        src_id = src_conf['id']
        shm_name = src_conf['shared_memory_name']
        queues = multi_pipe_queues.get(src_id, [])
        if not queues: 
            print(f"Info: No active pipelines for source '{src_id}'. Skipping streamer.")
            continue
        
        streamer = SourceStreamer(src_conf, shm_name, queues)
        streamer.start()
        processes.append(streamer)

    print(">>> All processes started. Each pipeline will have its own window.")

    try:
        aggregator.join()
    except KeyboardInterrupt:
        print("\n>>> Keyboard Interrupt.")
    finally:
        print(">>> Shutting down...")
        for p in processes:
            if hasattr(p, 'stop'):
                p.stop()
        # PipelineExecutor의 blocking get()이 종료 신호를 받을 수 있도록 None 센티널 전송
        for queues in multi_pipe_queues.values():
            for q in queues:
                try:
                    q.put(None)
                except Exception:
                    pass
        for p in processes:
            p.terminate()
            p.join()
        print(">>> Shutdown complete.")
