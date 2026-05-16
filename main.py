import multiprocessing as mp
import yaml
import argparse

from core.sources.streamer import SourceStreamer
from core.pipelines.executor import PipelineExecutor
from core.outputs.aggregator import OutputAggregator

if __name__ == "__main__":
    mp.set_start_method("spawn")
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default="configs/multi_cam.yaml")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

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
        p_in_q = mp.Queue()
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
            p.terminate()
            p.join()
        print(">>> Shutdown complete.")
